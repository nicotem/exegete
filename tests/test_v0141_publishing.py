# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: publishing both packages.

publish.yml builds `exegete` and the old name's `qualcoder-mcp`, checks
both, and uploads both in one step per index. A manual run (the
TestPyPI rehearsal) first gives both a practice version of their own,
so a rehearsal never uses up a release's file names; a release never
takes that step. The PyPI step skips files already uploaded, so a
release whose upload stopped half-way can be run again.
"""

import re
import shutil
import sys
from pathlib import Path

import pytest
from packaging.version import Version

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import practice_version as practice               # noqa: E402
from test_v012_workflow_pins import WORKFLOWS, _jobs   # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib


def _job(name):
    return {job["name"]: "\n".join(job["lines"])
            for job in _jobs(WORKFLOWS / "publish.yml")}[name]


def _steps(job_text):
    """[(name, text)] of each step in a job."""
    parts = re.split(r"(?m)^      - ", job_text)[1:]
    steps = []
    for part in parts:
        match = re.search(r"name: (.+)", part)
        steps.append((match.group(1).strip() if match else "", part))
    return steps


class TestThePracticeVersion:

    @pytest.mark.parametrize("release,run,expected", [
        ("0.14.1-alpha", 12, "0.14.1a0.dev12"),
        ("0.14.1a0", 1, "0.14.1a0.dev1"),
        ("1.0.0", 7, "1.0.0.dev7"),
    ])
    def test_the_rule(self, release, run, expected):
        assert practice.practice_version(release, run) == expected
        assert str(Version(expected)) == expected          # valid PEP 440
        assert Version(expected) < Version(release)

    def test_a_dev_version_is_refused(self):
        with pytest.raises(ValueError):
            practice.practice_version("0.14.1a0.dev3", 4)

    def test_both_files_get_it_and_the_floor(self, tmp_path):
        for name in (practice.MAIN, practice.OLD_NAME):
            (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, tmp_path / name)
        version = practice.apply(tmp_path, 42)
        with open(REPO / "pyproject.toml", "rb") as handle:
            release = tomllib.load(handle)["project"]["version"]
        assert version == f"{Version(release)}.dev42"
        with open(tmp_path / practice.MAIN, "rb") as handle:
            main = tomllib.load(handle)["project"]
        with open(tmp_path / practice.OLD_NAME, "rb") as handle:
            old = tomllib.load(handle)["project"]
        assert main["version"] == old["version"] == version
        assert old["dependencies"] == [f"exegete>={version}"]
        assert str(Version(version)) == version
        # nothing else in either file moved
        for name in (practice.MAIN, practice.OLD_NAME):
            before = (REPO / name).read_text(encoding="utf-8").splitlines()
            after = (tmp_path / name).read_text(
                encoding="utf-8").splitlines()
            changed = [a for b, a in zip(before, after) if a != b]
            assert len(before) == len(after)
            assert len(changed) == (1 if name == practice.MAIN else 2)

    def test_the_command_line(self, capsys):
        assert practice.main(["x"]) == 2
        assert practice.main([]) == 2


class TestTheWorkflow:

    def test_the_practice_step_runs_on_manual_runs_only(self):
        steps = _steps(_job("build"))
        names = [name for name, _ in steps]
        index = names.index("Practice version (manual runs only)")
        text = steps[index][1]
        assert "if: github.event_name == 'workflow_dispatch'" in text
        assert ('python scripts/practice_version.py '
                '"${{ github.run_number }}"') in text
        assert index < names.index("Build distributions")

    def test_it_builds_and_checks_both(self):
        build = dict(_steps(_job("build")))["Build distributions"]
        assert "python -m build\n" in build
        assert "python -m build packaging/pypi-old-name --outdir dist/" \
            in build
        check = dict(_steps(_job("build")))["Check distributions"]
        assert "python -m twine check --strict dist/*" in check

    def test_one_upload_step_per_index(self):
        for job in ("publish-to-testpypi", "publish-to-pypi"):
            text = _job(job)
            assert text.count("pypa/gh-action-pypi-publish@") == 1, job

    def test_the_pypi_step_skips_what_is_already_there(self):
        text = _job("publish-to-pypi")
        assert "skip-existing: true" in text
        assert "re-run the failed job" in text.lower()

    def test_the_project_pages_are_exegetes(self):
        assert "url: https://test.pypi.org/p/exegete" in \
            _job("publish-to-testpypi")
        assert "url: https://pypi.org/p/exegete" in _job("publish-to-pypi")

    def test_the_comments_name_the_four_publishers(self):
        text = (WORKFLOWS / "publish.yml").read_text(encoding="utf-8")
        head = text[:text.index("\non:")]
        for index in ("test.pypi.org", "pypi.org"):
            for project in ("qualcoder-mcp", "exegete"):
                assert re.search(rf"{re.escape(index)}\s+→ project "
                                 rf"{project}\b", head), (index, project)
        assert "letter case included" in head
        assert "`v*`" in head
