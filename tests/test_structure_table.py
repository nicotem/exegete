# SPDX-License-Identifier: LGPL-3.0-or-later
"""scripts/structure_table.py: the structural table kept per release.

The script measures one commit read through git: the largest files, the
most complex functions, how many functions each grade holds, and the
suite and CI from the inputs it is given. Pinned here: the table's
sections on this checkout's HEAD; the count, construct by construct;
the grades' bands; the code lines; the two inputs' readers; the
standard library alone; the long and complex list at both thresholds;
the refusal to write over a table of another commit, or over this
commit's suite and CI lines with "not given"; the refusal of a log of
part of the suite; and the tables kept for the releases measured so
far. Every test but the first and the last works on made-up texts, with
neither git nor the repository.
"""

import ast
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "structure_table.py"
A, B, C = "a" * 40, "b" * 40, "c" * 40


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("structure_table", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _section(text, heading):
    """The lines under one `## ` heading, up to the next."""
    part = text.split(f"\n## {heading}\n", 1)[1]
    return part.split("\n## ", 1)[0].strip("\n").split("\n")


@pytest.fixture(scope="module")
def head_table(script, tmp_path_factory):
    """The table of this checkout's HEAD, made once for the module."""
    if shutil.which("git") is None or subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=str(REPO),
            capture_output=True).returncode != 0:
        pytest.skip("not a git checkout")
    out = tmp_path_factory.mktemp("structure") / "table.md"
    assert script.main(["--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


def test_the_table_has_its_sections(script, head_table):
    headings = re.findall(r"^## (.+)$", head_table, re.M)
    assert headings == list(script.HEADINGS)
    for heading in script.HEADINGS[:2]:
        rows = [line for line in _section(head_table, heading)
                if line.startswith("| `")]
        for tree in ("src", "tests"):
            assert len([r for r in rows if r.startswith(f"| `{tree}/")]) \
                == 10, (heading, tree)
    for tree in ("src", "tests"):
        tree_id = subprocess.run(
            ["git", "rev-parse", f"HEAD:{tree}"], cwd=str(REPO),
            capture_output=True, text=True, check=True).stdout.strip()
        assert f"`{tree_id}`" in head_table, tree
    last = [line for line in _section(head_table, script.HEADINGS[3])
            if line.startswith("- ")]
    assert len(last) == 6
    assert all(line.endswith(": not given") for line in last), last


# A function's body for each construct, and the count it makes
def _case(name, body, count, *marks):
    return pytest.param(body, count, id=name, marks=marks)


CONSTRUCTS = [
    _case("if", "if a:\n    pass", 2),
    _case("elif", "if a:\n    pass\nelif b:\n    pass\nelse:\n    pass", 3),
    _case("conditional-expression", "x = a if b else c", 2),
    _case("for", "for x in y:\n    pass", 2),
    _case("for-else", "for x in y:\n    pass\nelse:\n    pass", 3),
    _case("async-for", "async for x in y:\n    pass", 2),
    _case("while", "while a:\n    pass", 2),
    _case("while-else", "while a:\n    pass\nelse:\n    pass", 3),
    _case("except", "try:\n    pass\nexcept E:\n    pass\n"
          "except F:\n    pass", 3),
    _case("except-star", "try:\n    pass\nexcept* E:\n    pass", 2,
          pytest.mark.skipif(sys.version_info < (3, 11),
                             reason="except* is Python 3.11's")),
    _case("try-else-finally", "try:\n    pass\nexcept E:\n    pass\n"
          "else:\n    pass\nfinally:\n    pass", 2),
    _case("with", "with a as b, c:\n    pass", 2),
    _case("async-with", "async with a:\n    pass", 2),
    _case("assert", "assert a", 2),
    _case("comprehension", "x = [a for a in b for c in a]", 3),
    _case("comprehension-if", "x = {a for a in b if a if c}", 4),
    _case("and", "x = a and b and c", 3),
    _case("or", "x = a or b", 2),
    _case("match-case", "match a:\n    case 1:\n        pass\n"
          "    case _:\n        pass", 3),
    _case("lambda", "f = lambda: a if b else c", 2),
]


@pytest.mark.parametrize("body, count", CONSTRUCTS)
def test_each_construct_adds_one(script, body, count):
    source = "async def f():\n" + "".join(
        f"    {line}\n" for line in body.split("\n"))
    (function,) = script.measure({"src/m.py": source})[1]
    assert (function.name, function.count) == ("f", count)


def test_a_nested_function_or_class_adds_nothing_to_its_parent(script):
    source = ("def outer():\n    if a:\n        pass\n"
              "    def inner():\n        if b:\n            pass\n"
              "        return [c for c in d]\n"
              "    class K:\n        def m(self):\n            assert e\n"
              "    return inner\n")
    counts = {f.name: f.count for f in script.measure({"src/m.py": source})[1]}
    assert counts == {"outer": 2, "outer.inner": 3, "outer.K.m": 2}


@pytest.mark.parametrize("count, letter", [
    (1, "A"), (5, "A"), (6, "B"), (10, "B"), (11, "C"), (20, "C"),
    (21, "D"), (30, "D"), (31, "E"), (40, "E"), (41, "F"), (400, "F")])
def test_the_grades_follow_the_bands(script, count, letter):
    assert script.grade(count) == letter


def test_code_lines_leave_out_strings_and_comments(script):
    source = ('def f():\n'                        # 1 code
              '    """A docstring\n'              # 2 the string alone
              '    over two lines."""\n'          # 3 string
              '    # a comment line\n'            # 4 comment
              '\n'                                # 5 blank
              '    text = """a text\n'            # 6 code before it
              'over\n'                            # 7 string
              'three lines"""\n'                  # 8 string
              '    pieces = ("one piece "\n'      # 9 code before it
              '              "beside another")\n'  # 10 the same string
              '    return text  # a comment\n')   # 11 code
    (file,), (function,) = script.measure({"src/m.py": source})
    assert (function.lines, function.code_lines) == (11, 4)
    assert (file.lines, file.code_lines) == (11, 4)


def test_windows_line_ends_change_nothing(script):
    """A Windows checkout's git archive gives its text with \\r\\n."""
    assert script.read_version(
        '[project]\r\nname = "exegete"\r\nversion = "0.15.2-alpha"\r\n'
    ) == "0.15.2-alpha"
    source = ('def f():\n    """A text\n    over two lines."""\n'
              '    # a comment\n\n    return [a for a in b if a]\n')
    for ends in ("\r\n", "\r"):
        assert script.measure({"src/m.py": source.replace("\n", ends)}) \
            == script.measure({"src/m.py": source}), repr(ends)


def _made_up(script, monkeypatch, sources, commit=A):
    """The git readers replaced by a made-up commit and its texts."""
    monkeypatch.setattr(script, "read_commit", lambda ref: script.Commit(
        commit, {"src": B, "tests": C}, "2026-10-23"))
    monkeypatch.setattr(script, "read_archive", lambda commit: (
        dict(sources), 'version = "9.9.9-alpha"\n'))


LOG = "\n".join([
    "============================= test session starts =============",
    "platform darwin -- Python 3.13.5, pytest-8.4.2, pluggy-1.6.0",
    "collected 10147 items", "",
    "tests/test_made_up.py ....                                [100%]", "",
    "======= 10097 passed, 50 skipped in 1013.20s (0:16:53) ========", ""])
RUN = {"conclusion": "success", "headSha": A,
       "startedAt": "2026-10-23T18:00:00Z", "jobs": [
           {"name": "Linux", "startedAt": "2026-10-23T18:00:05Z",
            "completedAt": "2026-10-23T18:10:05Z"},
           {"name": "Windows, part 1", "startedAt": "2026-10-23T18:00:10Z",
            "completedAt": "2026-10-23T18:33:12Z"},
           {"name": "Documents", "startedAt": "2026-10-23T18:00:07Z",
            "completedAt": "2026-10-23T18:01:07Z"}]}


def test_the_inputs_are_read(script, monkeypatch, tmp_path):
    _made_up(script, monkeypatch, {"src/m.py": "def f():\n    pass\n"})
    log, run, out = (tmp_path / "suite.log", tmp_path / "run.json",
                     tmp_path / "table.md")
    log.write_text(LOG, encoding="utf-8")
    run.write_text(json.dumps(RUN), encoding="utf-8")
    assert script.main(["--out", str(out), "--pytest-log", str(log),
                        "--ci-run", str(run), "--ci-attempts", "2"]) == 0
    table = out.read_text(encoding="utf-8")
    last = _section(table, "The suite and CI")
    assert "Python 3.13.5" in last[0]
    assert "10,097 passed" in last[1] and "16 min 53 s" in last[1]
    assert last[2].endswith("(the commit measured)")
    assert "33 min 12 s" in last[3]  # the run's start to the last job's end
    assert last[4].endswith(": 2")
    jobs = [line[4:].split(":")[0] for line in last if line.startswith("  - ")]
    assert jobs == ["Windows, part 1", "Linux", "Documents"]
    assert script.NOT_GIVEN not in "\n".join(last)
    # the files measured are the trees' Python files alone
    assert _section(table, "Largest files")[0] == (
        "The ten longest Python files of each tree, by lines.")
    assert _section(table, "Functions by grade")[0].startswith(
        "In `src/`, 1 functions in 1 Python files; in `tests/`, 0 in 0.")


@pytest.mark.parametrize("head, said", [
    (A, "success, at commit `aaaaaaa` (the commit measured)"),
    (B, "success, at commit `bbbbbbb` (not the commit measured)"),
    (None, "success, at commit not given")])
def test_ci_s_commit_is_compared_with_the_commit_measured(script, head,
                                                          said):
    run = dict(RUN, headSha=head) if head else {
        key: value for key, value in RUN.items() if key != "headSha"}
    lines = script._suite_and_ci(A, None, script.read_ci_run(run), None)
    assert lines[2] == f"- CI's run, its first attempt: {said}"


def test_only_the_standard_library():
    imported = set()
    for node in ast.walk(ast.parse(SCRIPT.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert "subprocess" in imported and "ast" in imported
    assert imported <= set(sys.stdlib_module_names), imported
    assert not imported & {"socket", "ssl", "http", "urllib", "exegete"}


def test_the_long_and_complex_list(script, monkeypatch, tmp_path, capsys):
    def ifs(name, many):
        return f"def {name}():\n" + "".join(
            f"    if a{i}:\n        pass\n" for i in range(many))

    def long(name, code_lines):
        return f"def {name}():\n" + "".join(
            f"    x{i} = {i}\n" for i in range(code_lines - 1))
    _made_up(script, monkeypatch, {"src/m.py": (
        ifs("twenty_ifs", 20) + ifs("nineteen_ifs", 19)
        + long("lines_201", 201) + long("lines_200", 200))})
    def kept():
        folder = REPO / "docs" / "structure"
        return sorted((p.name, p.stat().st_mtime_ns)
                      for p in folder.iterdir()) if folder.is_dir() else []
    before = kept()
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    assert script.main(["--functions"]) == 0
    listed = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in listed] == ["lines_201",
                                                   "twenty_ifs"]
    assert "201" in listed[0] and "21" in listed[1]
    assert list(work.iterdir()) == []  # it writes nothing
    assert kept() == before


def test_a_table_of_another_commit_is_kept(script, monkeypatch, tmp_path):
    out = tmp_path / "table.md"
    out.write_text(f"# A table\n\nMeasured at commit `{B}`, dated 1 "
                   "October 2026.\n", encoding="utf-8")
    before = out.read_bytes()
    with pytest.raises(script.Refused):
        script.check_kept(out, A, replace=False)
    _made_up(script, monkeypatch, {"src/m.py": "def f():\n    pass\n"})
    measured = script.measure
    monkeypatch.setattr(script, "measure", lambda sources: pytest.fail(
        "measured before the check"))
    assert script.main(["--out", str(out)]) == 2
    assert out.read_bytes() == before
    unnamed = tmp_path / "unnamed.md"
    unnamed.write_text("# A table with no commit\n", encoding="utf-8")
    with pytest.raises(script.Refused):
        script.check_kept(unnamed, A, replace=False)
    # let through: no file, the same commit, and --replace
    script.check_kept(tmp_path / "none.md", A, replace=False)
    script.check_kept(out, B, replace=False)
    script.check_kept(out, A, replace=True)
    monkeypatch.setattr(script, "measure", measured)
    assert script.main(["--out", str(out), "--replace"]) == 0
    assert f"Measured at commit `{A}`" in out.read_text(encoding="utf-8")


def test_this_commit_s_table_keeps_its_suite_and_ci(script, monkeypatch,
                                                    tmp_path):
    """A table of the commit measured is written again only with the
    inputs that gave its suite and CI lines, or with --replace."""
    _made_up(script, monkeypatch, {"src/m.py": "def f():\n    pass\n"})
    log, run, out = (tmp_path / "suite.log", tmp_path / "run.json",
                     tmp_path / "table.md")
    log.write_text(LOG, encoding="utf-8")
    run.write_text(json.dumps(RUN), encoding="utf-8")
    inputs = {"--pytest-log": str(log), "--ci-run": str(run),
              "--ci-attempts": "1"}
    every = [part for pair in inputs.items() for part in pair]
    assert script.main(["--out", str(out)] + every) == 0
    kept = out.read_bytes()
    for left_out in inputs:
        given = [part for option, value in inputs.items()
                 if option != left_out for part in (option, value)]
        assert script.main(["--out", str(out)] + given) == 2, left_out
        assert out.read_bytes() == kept, left_out
    assert script.main(["--out", str(out)] + every) == 0
    assert out.read_bytes() == kept
    assert script.main(["--out", str(out), "--replace"]) == 0
    last = _section(out.read_text(encoding="utf-8"), "The suite and CI")
    assert all(line.endswith(script.NOT_GIVEN) for line in last), last
    # its lines all "not given", it is written again without inputs
    assert script.main(["--out", str(out)]) == 0


def _log(collected, summary):
    """A pytest log with its collected line, if any, and its summary."""
    return "\n".join([
        "platform linux -- Python 3.13.5, pytest-8.4.2, pluggy-1.6.0"]
        + ([collected] if collected else [])
        + ["", "tests/test_made_up.py ....", "", f"==== {summary} ====", ""])


# A log, and what its refusal names: the kind, or the counts
@pytest.mark.parametrize("collected, summary, named", [
    ("collected 10160 items / 10117 deselected / 43 selected",
     "43 passed, 10117 deselected in 3.00s", "10,117 deselected"),
    ("collected 10 items", "9 passed, 1 xfailed in 1.00s", "1 xfailed"),
    # two errors make up the count: refused for the xpassed alone
    ("collected 10 items", "8 passed, 1 xpassed, 2 errors in 1.00s",
     "1 xpassed"),
    ("collected 10160 items", "5000 passed, 20 skipped in 400.00s",
     "5,020 of the 10,160"),
    ("collected 10 items / 2 errors", "2 errors in 0.50s", "0 of the 10"),
    (None, "10097 passed, 50 skipped in 1013.20s", "-q")],
    ids=["deselected", "xfailed", "xpassed", "stopped-early",
         "collection-errors", "no-collected-line"])
def test_a_log_of_part_of_the_suite_is_refused(script, monkeypatch, tmp_path,
                                               capsys, collected, summary,
                                               named):
    _made_up(script, monkeypatch, {"src/m.py": "def f():\n    pass\n"})
    log, out = tmp_path / "suite.log", tmp_path / "table.md"
    log.write_text(_log(collected, summary), encoding="utf-8")
    assert script.main(["--out", str(out), "--pytest-log", str(log)]) == 1
    assert not out.exists()
    assert named in capsys.readouterr().err


@pytest.mark.parametrize("collected, summary, said", [
    ("collected 10 items", "9 passed, 1 error in 1.00s",
     "9 passed, 0 skipped, 0 failed, 1 error, in 1 s"),
    ("collected 10 items", "8 passed, 2 errors in 1.00s",
     "8 passed, 0 skipped, 0 failed, 2 errors, in 1 s"),
    # an error at a test's tear-down, beside its outcome
    ("collected 10 items", "10 passed, 1 error in 1.00s",
     "10 passed, 0 skipped, 0 failed, 1 error, in 1 s"),
    # a module skipped whole: among the skipped, not the collected
    ("collected 10 items / 1 skipped", "10 passed, 1 skipped in 1.00s",
     "10 passed, 1 skipped, 0 failed, in 1 s"),
    ("collecting 3 items\rcollected 10 items", "8 passed, 2 skipped in 61.00s",
     "8 passed, 2 skipped, 0 failed, in 1 min 1 s")],
    ids=["one-error", "two-errors", "tear-down", "module-skipped",
         "terminal"])
def test_a_log_of_the_whole_suite_is_read(script, collected, summary, said):
    assert script.read_pytest_log(_log(collected, summary))["suite"] == said


@pytest.mark.parametrize("version, commit", [
    ("0.14.3-alpha", "0e8a83e"), ("0.15.0-alpha", "b5897c8"),
    ("0.15.1-alpha.1", "171610e")])
def test_the_release_tables_are_kept(script, version, commit):
    text = (REPO / "docs" / "structure" / f"{version}.md").read_text(
        encoding="utf-8")
    measured = re.search(r"Measured at commit `([0-9a-f]{40})`", text)
    assert measured and measured.group(1).startswith(commit)
    assert re.findall(r"^## (.+)$", text, re.M) == list(script.HEADINGS)
