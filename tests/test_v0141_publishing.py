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
import release_version as tagged                  # noqa: E402
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


class TestTheEarlyBuild:
    """v0.14.1 (the owner's ruling 41, decision 10): a GitHub pre-release
    tagged with the coming release's version plus `.devN` builds and
    uploads `exegete` alone at that development version, to hold the
    name; never the old name's package. Any other tag refuses."""

    @pytest.mark.parametrize("release,tag,expected", [
        ("0.14.1-alpha", "v0.14.1-alpha.dev1", "0.14.1a0.dev1"),
        ("0.14.1-alpha", "v0.14.1-alpha.dev12", "0.14.1a0.dev12"),
        ("1.0.0", "v1.0.0.dev3", "1.0.0.dev3"),
    ])
    def test_an_early_tag(self, release, tag, expected):
        assert tagged.classify(release, tag, True) == ("early", expected)
        assert str(Version(expected)) == expected          # valid PEP 440
        assert Version(expected) < Version(release)

    def test_a_release_tag(self):
        assert tagged.classify("0.14.1-alpha", "v0.14.1-alpha", True) == \
            ("release", "0.14.1a0")
        assert tagged.classify("0.14.1-alpha", "v0.14.1-alpha", False) == \
            ("release", "0.14.1a0")

    @pytest.mark.parametrize("tag,prerelease", [
        ("v0.14.1-alpha.dev1", False),        # an early build, not marked
        ("v0.14.2-alpha.dev1", True),         # another release's version
        ("v0.14.0-alpha.dev1", True),
        ("v0.14.1a0.dev1", True),             # not the pyproject spelling
        ("0.14.1-alpha.dev1", True),          # no v
        ("v0.14.1-alpha.dev", True),
        ("v0.14.1-alpha.dev1x", True),
        ("v0.14.1-alpha-dev1", True),
        ("v0.14.1-alpha.post1", True),
        ("v0.14.1-alpha.dev1\n", True),
    ])
    def test_every_other_tag_is_refused(self, tag, prerelease):
        with pytest.raises(tagged.Refused):
            tagged.classify("0.14.1-alpha", tag, prerelease)

    def _tree(self, tmp_path, version="0.14.1-alpha"):
        for name in (practice.MAIN, practice.OLD_NAME):
            (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
            text = (REPO / name).read_text(encoding="utf-8")
            text = re.sub(r'(?m)^version = "[^"]+"$',
                          f'version = "{version}"', text, count=1)
            (tmp_path / name).write_text(text, encoding="utf-8")
        return {name: (tmp_path / name).read_text(encoding="utf-8")
                for name in (practice.MAIN, practice.OLD_NAME)}

    def test_an_early_build_changes_the_version_line_alone(self, tmp_path):
        before = self._tree(tmp_path)
        assert tagged.apply(tmp_path, "v0.14.1-alpha.dev2", True) == \
            ("early", "0.14.1a0.dev2")
        with open(tmp_path / practice.MAIN, "rb") as handle:
            assert tomllib.load(handle)["project"]["version"] == \
                "0.14.1a0.dev2"
        after = (tmp_path / practice.MAIN).read_text(encoding="utf-8")
        changed = [a for b, a in zip(before[practice.MAIN].splitlines(),
                                     after.splitlines()) if a != b]
        assert changed == ['version = "0.14.1a0.dev2"']
        # the old name's package is not touched (and not built)
        assert (tmp_path / practice.OLD_NAME).read_text(
            encoding="utf-8") == before[practice.OLD_NAME]

    def test_a_release_changes_nothing(self, tmp_path):
        before = self._tree(tmp_path)
        assert tagged.apply(tmp_path, "v0.14.1-alpha", False)[0] == \
            "release"
        for name, text in before.items():
            assert (tmp_path / name).read_text(encoding="utf-8") == text

    def test_the_tree_s_own_version_decides(self):
        with open(REPO / "pyproject.toml", "rb") as handle:
            release = tomllib.load(handle)["project"]["version"]
        assert tagged.classify(release, f"v{release}.dev1", True)[0] == \
            "early"
        with pytest.raises(tagged.Refused):
            tagged.classify(release, "v99.0.0.dev1", True)

    def test_the_command_line(self, capsys, monkeypatch, tmp_path):
        assert tagged.main(["v1"]) == 2
        assert tagged.main(["v1", "yes"]) == 2
        self._tree(tmp_path)
        monkeypatch.setattr(tagged, "REPO", tmp_path)
        assert tagged.main(["v9.9.9", "true"]) == 1
        assert "Refused:" in capsys.readouterr().err
        assert tagged.main(["v0.14.1-alpha.dev3", "true"]) == 0
        assert capsys.readouterr().out == \
            "kind=early\nversion=0.14.1a0.dev3\n"

    def test_the_workflow_asks_the_tag_first_on_releases_only(self):
        steps = _steps(_job("build"))
        names = [name for name, _ in steps]
        text = dict(steps)["Version from the tag (releases only)"]
        assert "if: github.event_name == 'release'" in text
        assert "id: tag" in text
        # the tag reaches the script through the environment only
        assert "TAG: ${{ github.event.release.tag_name }}" in text
        assert "PRERELEASE: ${{ github.event.release.prerelease }}" in text
        run = re.search(r"run: (.+)", text).group(1)
        assert run == ('python scripts/release_version.py "$TAG" '
                       '"$PRERELEASE" >> "$GITHUB_OUTPUT"')
        assert names.index("Install build tooling") < names.index(
            "Version from the tag (releases only)") < names.index(
            "Build distributions")

    def test_an_early_build_never_builds_the_old_name(self):
        steps = dict(_steps(_job("build")))
        build = steps["Build distributions"]
        assert "KIND: ${{ steps.tag.outputs.kind }}" in build
        old = build.index("python -m build packaging/pypi-old-name")
        assert build.rindex('if [ "$KIND" != "early" ]; then', 0, old) \
            < old
        guard = steps["An early build holds exegete alone"]
        assert "if: steps.tag.outputs.kind == 'early'" in guard
        assert 'test "$(ls dist/ | wc -l)" -eq 2' in guard

    def test_the_rehearsal_and_the_upload_are_unchanged(self):
        steps = dict(_steps(_job("build")))
        assert "if: github.event_name == 'workflow_dispatch'" in \
            steps["Practice version (manual runs only)"]
        pypi = _job("publish-to-pypi")
        assert ("if: github.event_name == 'release' && "
                "github.event.action == 'published'") in pypi
        assert "name: pypi" in pypi
        assert "kind" not in pypi
