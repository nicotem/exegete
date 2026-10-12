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

    def test_reading_it_takes_it_out_of_the_environment(self, monkeypatch):
        monkeypatch.setenv(VARIABLE, "2/3")
        config = SimpleNamespace(stash=pytest.Stash())
        conftest.pytest_configure(config)
        assert VARIABLE not in os.environ
        assert config.stash[conftest.TEST_PART_KEY] == (2, 3)


class TestTheHook:

    @staticmethod
    def _run(chosen, nodeids):
        deselected = []
        config = SimpleNamespace(
            stash=pytest.Stash(),
            hook=SimpleNamespace(pytest_deselected=lambda items:
                                 deselected.extend(items)))
        config.stash[conftest.TEST_PART_KEY] = chosen
        items = [SimpleNamespace(nodeid=nodeid) for nodeid in nodeids]
        conftest.pytest_collection_modifyitems(config, items)
        return ([item.nodeid for item in items],
                [item.nodeid for item in deselected])

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
    env = dict(os.environ)
    env[VARIABLE] = "1/1"
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--basetemp={tmp_path / 'child-base'}",
         f"tests/{Path(__file__).name}::test_no_test_sees_the_variable"],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr
    assert "1 passed" in result.stdout, result.stdout[-2000:]


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

