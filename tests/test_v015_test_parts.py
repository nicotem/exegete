# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15, the groundwork: the suite in parts.

CI runs Windows' suite in three jobs, a part each
(.github/workflows/ci.yml): `EXEGETE_TEST_SHARD="k/n"` keeps part k of n
(tests/conftest.py). Checked here: the split itself, made of whole files
weighed by their number of tests; the variable's reading; the hook that
keeps a part; and that the variable leaves the environment before any
test runs, so the suite's own inner runs, which copy the environment and
load the same conftest, run whole.
"""

import itertools
import os
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

# The conftest pytest loaded, under its package name: `import conftest`
# would load a second copy, whose start-of-run hooks never ran
# (test_suite_hygiene.py reads every copy's baseline).
from tests import conftest

REPO = Path(__file__).resolve().parents[1]
VARIABLE = "EXEGETE_TEST_SHARD"

# Files of these sizes, in tests: the suite's three largest as collected
# at 0.14.3, a tail of small ones, and ties, which the split breaks by
# path.
SIZES = [663, 403, 227, 120, 97, 60, 41, 40, 40, 12, 7, 3, 1, 1]


def _nodeids(sizes):
    """Node ids for files of these sizes, as pytest writes them; a
    parameter may itself hold "::"."""
    nodeids = []
    for number, size in enumerate(sizes):
        path = f"tests/test_{number:03}.py"
        for test in range(size):
            nodeids.append(f"{path}::TestA::test_{test}[a::b-{test}]")
    return nodeids


def _parts_by_file(nodeids, parts):
    """Each file's set of part numbers."""
    by_file = {}
    for nodeid, number in zip(nodeids, conftest.parts_of(nodeids, parts)):
        by_file.setdefault(nodeid.split("::", 1)[0], set()).add(number)
    return by_file


class TestTheSplit:

    @pytest.mark.parametrize("parts", [1, 2, 3, 4, 7])
    def test_each_file_is_in_exactly_one_part(self, parts):
        by_file = _parts_by_file(_nodeids(SIZES), parts)
        assert len(by_file) == len(SIZES)
        assert all(len(numbers) == 1 for numbers in by_file.values()), \
            by_file
        assert set().union(*by_file.values()) <= set(range(1, parts + 1))

    def test_the_same_parts_in_any_input_order(self):
        nodeids = _nodeids(SIZES)
        expected = _parts_by_file(nodeids, 3)
        for seed in range(5):
            shuffled = nodeids[:]
            random.Random(seed).shuffle(shuffled)
            assert _parts_by_file(shuffled, 3) == expected, seed

    @pytest.mark.parametrize("parts", [2, 3, 5])
    def test_no_part_is_empty_while_files_outnumber_parts(self, parts):
        for files in range(parts + 1, parts + 6):
            # one large file and the rest of one test each
            nodeids = _nodeids([SIZES[0]] + [1] * (files - 1))
            assert set(conftest.parts_of(nodeids, parts)) == \
                set(range(1, parts + 1)), files

    @pytest.mark.parametrize("parts", [2, 3, 4])
    def test_the_parts_are_within_the_largest_files_count(self, parts):
        rng = random.Random(parts)
        for _ in range(20):
            sizes = [rng.randint(1, 300)
                     for _ in range(rng.randint(parts, 40))]
            totals = Counter(conftest.parts_of(_nodeids(sizes), parts))
            counts = [totals.get(number, 0)
                      for number in range(1, parts + 1)]
            assert max(counts) - min(counts) <= max(sizes), (sizes, counts)

    def test_one_part_of_one_is_every_test(self):
        assert conftest.parse_test_part("1/1") == (1, 1)
        nodeids = _nodeids(SIZES)
        assert conftest.parts_of(nodeids, 1) == [1] * len(nodeids)

    @pytest.mark.parametrize("sizes, parts, expected", [
        # Largest first: in path order, a, c and d would share part 1.
        # Ties between parts to the lower number: sent to the higher, a
        # and b would be in part 2.
        ({"a": 1, "b": 3, "c": 2, "d": 2}, 2,
         {"a": 1, "b": 1, "c": 2, "d": 2}),
        # Ties between files of one size by path: in the reverse order, b
        # would be in part 1 and a in part 2.
        ({"a": 2, "b": 2, "c": 1}, 2, {"a": 1, "b": 2, "c": 1}),
        # Each file into the part with the fewest tests so far: taken in
        # turn instead, z would be in part 1.
        ({"v": 2, "w": 3, "x": 5, "y": 4, "z": 3}, 3,
         {"v": 2, "w": 3, "x": 1, "y": 2, "z": 3}),
    ])
    def test_the_parts_written_out(self, sizes, parts, expected):
        """Small suites in which each of the split's rules changes the
        answer, written out in full, so that a change to any rule turns
        red even where the parts stay as even."""
        nodeids = [f"tests/test_{name}.py::test_{number}"
                   for name, size in sizes.items()
                   for number in range(size)]
        got = {}
        for nodeid, number in zip(nodeids, conftest.parts_of(nodeids, parts)):
            got[nodeid.split("::", 1)[0][len("tests/test_"):-len(".py")]] = \
                number
        assert got == expected


class TestTheVariable:

    @pytest.mark.parametrize("value, expected", [
        (None, None), ("", None), ("1/3", (1, 3)), ("2/3", (2, 3)),
        ("3/3", (3, 3))])
    def test_a_part_or_every_test(self, value, expected):
        assert conftest.parse_test_part(value) == expected

    @pytest.mark.parametrize("value", ["0/3", "4/3", "3", "a/b", "1/0"])
    def test_anything_else_is_refused(self, value):
        with pytest.raises(pytest.UsageError, match=VARIABLE):
            conftest.parse_test_part(value)

    def test_at_most_a_hundred_parts(self):
        """A number of parts the split could not use, or a number too
        long to read, is refused like any other value, before
        collection, rather than leaving the run to run out of memory or
        to stop on Python's own error."""
        assert conftest.parse_test_part("100/100") == (100, 100)
        for value in ("1/101", "101/101", "1/1000000000000",
                      "1/" + "9" * 5000):
            with pytest.raises(pytest.UsageError, match=VARIABLE):
                conftest.parse_test_part(value)

    def test_reading_it_takes_it_out_of_the_environment(self, monkeypatch):
        monkeypatch.setenv(VARIABLE, "2/3")
        config = SimpleNamespace(stash=pytest.Stash())
        conftest.pytest_configure(config)
        assert VARIABLE not in os.environ
        assert config.stash[conftest.TEST_PART_KEY] == (2, 3)


def _hook(chosen, nodeids):
    """The kept node ids, the deselected ones and the config, after the
    conftest's hook has run on these node ids with this part chosen."""
    deselected = []
    config = SimpleNamespace(
        stash=pytest.Stash(),
        hook=SimpleNamespace(pytest_deselected=lambda items:
                             deselected.extend(items)))
    config.stash[conftest.TEST_PART_KEY] = chosen
    items = [SimpleNamespace(nodeid=nodeid) for nodeid in nodeids]
    conftest.pytest_collection_modifyitems(config, items)
    return ([item.nodeid for item in items],
            [item.nodeid for item in deselected], config)


class TestTheHook:

    @staticmethod
    def _run(chosen, nodeids):
        kept, deselected, _ = _hook(chosen, nodeids)
        return kept, deselected

    def test_the_part_is_kept_in_order_and_the_rest_deselected(self):
        nodeids = _nodeids(SIZES)
        random.Random(15).shuffle(nodeids)
        numbers = conftest.parts_of(nodeids, 3)
        kept_in_all = []
        for part in (1, 2, 3):
            kept, deselected = self._run((part, 3), nodeids)
            assert kept == [nodeid for nodeid, number
                            in zip(nodeids, numbers) if number == part]
            assert deselected == [nodeid for nodeid, number
                                  in zip(nodeids, numbers) if number != part]
            kept_in_all += kept
        assert sorted(kept_in_all) == sorted(nodeids)

    def test_without_a_part_every_test_stays(self):
        nodeids = _nodeids(SIZES)
        assert self._run(None, nodeids) == (nodeids, [])


LINE = re.compile(r"test part: ([0-9]+) of ([0-9]+), ([0-9]+) of ([0-9]+) "
                  r"files, ([0-9]+) of ([0-9]+) tests, split ([0-9a-f]{12})")


class TestTheLine:
    """Each part ends its run with one line: its share of the files and
    tests, and a fingerprint of the whole split. Nothing compares the
    three Windows jobs of one Python; with the line, the three can be
    compared from the run page, and the same fingerprint in all three
    means each file ran in exactly one part."""

    @staticmethod
    def _summary(config):
        written = []
        reporter = SimpleNamespace(stats={}, write_line=written.append)
        conftest.pytest_terminal_summary(reporter, 0, config)
        return [line for line in written if line.startswith("test part: ")]

    def test_each_part_ends_with_its_share_and_the_same_split(self):
        nodeids = _nodeids(SIZES)
        found = []
        for part in (1, 2, 3):
            # each job collects alike, though not necessarily in one order
            shuffled = nodeids[:]
            random.Random(part).shuffle(shuffled)
            kept, _, config = _hook((part, 3), shuffled)
            lines = self._summary(config)
            assert len(lines) == 1, lines
            match = LINE.fullmatch(lines[0])
            assert match is not None, lines[0]
            found.append(match.groups())
            assert match.group(1, 2) == (str(part), "3")
            assert int(match[3]) == len({nodeid.split("::", 1)[0]
                                         for nodeid in kept})
            assert int(match[5]) == len(kept)
        assert {(row[3], row[5], row[6]) for row in found} == {
            (str(len(SIZES)), str(len(nodeids)), found[0][6])}
        assert sum(int(row[2]) for row in found) == len(SIZES)
        assert sum(int(row[4]) for row in found) == len(nodeids)

    def test_a_different_split_has_a_different_fingerprint(self):
        """One job collecting one file's tests differently, enough to move
        files between parts, shows in its line."""
        nodeids = _nodeids(SIZES)
        other = _nodeids([SIZES[0] - 600] + SIZES[1:])
        assert _parts_by_file(nodeids, 3) != _parts_by_file(other, 3)
        lines = [self._summary(_hook((1, 3), ids)[2])[0]
                 for ids in (nodeids, other)]
        assert LINE.fullmatch(lines[0])[7] != LINE.fullmatch(lines[1])[7]

    def test_without_a_part_no_line(self):
        _, _, config = _hook(None, _nodeids(SIZES))
        assert self._summary(config) == []


def _child_run(tmp_path):
    """A child pytest given "1/1" in a copy of this environment, under
    this repository's conftest, on this file's probe test."""
    env = dict(os.environ)
    env[VARIABLE] = "1/1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--basetemp={tmp_path / 'child-base'}",
         f"tests/{Path(__file__).name}::test_no_test_sees_the_variable"],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=300)


def test_no_test_sees_the_variable():
    """The probe the next test runs in a child pytest: by the time a test
    runs, the variable has left the environment."""
    assert VARIABLE not in os.environ


def test_the_variable_is_gone_before_any_test_runs(tmp_path):
    """A child pytest given "1/1" in a copy of this environment, under
    this repository's conftest: its probe passes only if the variable
    was taken out before the tests ran. Without that, the suite's own
    inner runs (tests/test_v014_workspace_setting.py and
    track5_helpers.run_pytest_in_a_child) would split their one file."""
    result = _child_run(tmp_path)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr
    assert "1 passed" in result.stdout, result.stdout[-2000:]


def test_a_part_says_so_at_the_end_of_its_run(tmp_path):
    """The line in a real run's summary, where CI finds it: so a run in
    parts, here or on a developer's computer where the variable was left
    set, says it was partial."""
    result = _child_run(tmp_path)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr
    lines = [line for line in result.stdout.splitlines()
             if line.startswith("test part: ")]
    assert len(lines) == 1, result.stdout[-2000:]
    match = LINE.fullmatch(lines[0])
    assert match is not None, lines[0]
    assert match.groups()[:6] == ("1", "1", "1", "1", "1", "1")


def test_ci_runs_windows_in_three_parts_and_the_rest_whole():
    """The `test` job: on Windows a job per part, given "k/3"; on Linux
    and macOS part 1 alone, given nothing, so every test runs there. Each
    Windows part has a job name, a summary heading and an artefact of its
    own (an artefact name used twice in one run is refused)."""
    from test_v012_workflow_pins import WORKFLOWS, _jobs
    job = next(job for job in _jobs(WORKFLOWS / "ci.yml")
               if job["name"] == "test")
    body = "\n".join(job["lines"])
    lines = [line.strip() for line in job["lines"]]
    assert "part: [1, 2, 3]" in lines
    assert sorted(re.findall(r"- os: (\S+)\n\s+part: (\d)", body)) == [
        ("macos-latest", "2"), ("macos-latest", "3"),
        ("ubuntu-latest", "2"), ("ubuntu-latest", "3")]
    step = body[body.index("- name: Run test suite"):
                body.index("- name: Upload pytest output")]
    assert (f"{VARIABLE}: ${{{{ matrix.os == 'windows-latest' && "
            f"format('{{0}}/3', matrix.part) || '' }}}}") in \
        [line.strip() for line in step.splitlines()]
    own = ("${{ matrix.os == 'windows-latest' && "
           "format(', part {0} of 3', matrix.part) || '' }}")
    assert ("name: tests (${{ matrix.os }}, "
            f"py${{{{ matrix.python-version }}}}{own})") in lines
    assert any(line.startswith('echo "### pytest: ')
               and line.endswith(f'{own}"') for line in lines)
    assert ("name: pytest-${{ matrix.os }}-py${{ matrix.python-version }}"
            "${{ matrix.os == 'windows-latest' && "
            "format('-part{0}', matrix.part) || '' }}") in lines



def test_ci_publishes_each_parts_line():
    """The part's line, copied into the step summary and, as the rate
    lines are, into a check-run annotation, which signed-out readers can
    see: so the three Windows parts of one Python can be compared from
    the run page."""
    workflow = (WORKFLOWS_FOLDER / "ci.yml").read_text(encoding="utf-8")
    step = workflow[workflow.index("- name: Run test suite"):
                    workflow.index("- name: Upload pytest output")]
    closing = step.index('} >> "$GITHUB_STEP_SUMMARY"')
    summary = step[step.rindex("{\n", 0, closing):closing]
    assert 'grep -E "^test part: " pytest_output.txt | head -1' in \
        [line.strip() for line in summary.splitlines()]
    outside = step[closing:]
    line = ("sed -n 's/^test part: /::notice title=test part::/p' "
            "pytest_output.txt | head -1")
    assert line in [row.strip() for row in outside.splitlines()]
    assert outside.index(line) < outside.index("exit $code")


WORKFLOWS_FOLDER = REPO / ".github" / "workflows"
NUMBER_WORDS = ("zero one two three four five six seven eight nine ten "
                "eleven twelve thirteen fourteen fifteen sixteen seventeen "
                "eighteen nineteen twenty twenty-one twenty-two "
                "twenty-three twenty-four twenty-five").split()


def _matrix_jobs(lines):
    """The number of jobs one workflow job makes: one without a matrix;
    else every combination of its lists less those `exclude` names, or
    its `include` entries when it has no lists. Any other shape is
    refused rather than miscounted."""
    start = next((index for index, line in enumerate(lines)
                  if line.strip() == "matrix:"), None)
    if start is None:
        return 1
    indent = len(lines[start]) - len(lines[start].lstrip())
    lists, entries, key = {}, {"include": [], "exclude": []}, None
    for line in lines[start + 1:]:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        depth = len(line) - len(line.lstrip())
        if depth <= indent:
            break
        name, colon, value = text.removeprefix("- ").partition(":")
        assert colon, line
        value = value.strip()
        if depth == indent + 2:
            key = name if name in entries and not value else None
            if key is None:
                assert value.startswith("[") and value.endswith("]"), line
                lists[name] = [item.strip().strip("\"'")
                               for item in value[1:-1].split(",")]
            continue
        assert key is not None, line
        if text.startswith("- "):
            entries[key].append({})
        entries[key][-1][name] = value.strip("\"'")
    assert not (lists and entries["include"]), lines[start]
    combinations = [dict(zip(lists, values))
                    for values in itertools.product(*lists.values())
                    ] if lists else []
    kept = [combination for combination in combinations
            if not any(all(combination.get(name) == value
                           for name, value in left_out.items())
                       for left_out in entries["exclude"])]
    return len(kept) + len(entries["include"])


def test_the_contributors_guide_counts_the_jobs_ci_runs():
    """CONTRIBUTING.md, item 5, says how many jobs CI runs and how many
    of them run the suite, and how to run one part: counted here from
    the workflow, so a job added or a matrix changed shows here until
    the guide says so too (it said ten jobs while CI ran fourteen)."""
    from test_v012_workflow_pins import _jobs
    counts = {job["name"]: _matrix_jobs(job["lines"])
              for job in _jobs(WORKFLOWS_FOLDER / "ci.yml")}
    test_lines = next(job["lines"] for job in _jobs(WORKFLOWS_FOLDER /
                                                     "ci.yml")
                      if job["name"] == "test")
    parts = re.search(r"part: \[([^\]]*)\]", "\n".join(test_lines))
    guide = " ".join((REPO / "CONTRIBUTING.md").read_text(
        encoding="utf-8").split())
    item = guide[guide.index("5. **Continuous integration**"):
                 guide.index("6. **Document the change.**")]
    assert f"{NUMBER_WORDS[sum(counts.values())]} jobs" in item, counts
    assert f"{NUMBER_WORDS[counts['test']].capitalize()} run the suite" \
        in item, counts
    assert f"{NUMBER_WORDS[len(parts[1].split(','))]} parts" in item
    assert f"`{VARIABLE}`" in item
