# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: the old name's package, and what each wheel holds.

`qualcoder-mcp` on PyPI becomes a small package, released beside every
Exegete release until v1.0 (packaging/pypi-old-name): the old command
and a two-file stand-in `qualcoder_mcp`, depending on `exegete`. The
layout was measured (the rename study): the old command and the old
module must be in the old name's package and never in `exegete`'s, or
`pip install --upgrade qualcoder-mcp` deletes them.
"""

import zipfile
import tarfile
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

import rename_helpers as rh

REPO = rh.REPO
OLD = REPO / rh.OLD_NAME_DIR

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib


def _toml(path):
    with open(path, "rb") as handle:
        return tomllib.load(handle)


MAIN_META = _toml(REPO / "pyproject.toml")["project"]
OLD_PROJECT = _toml(OLD / "pyproject.toml")
OLD_META = OLD_PROJECT["project"]
STAND_IN = ("__init__.py", "server.py")


class TestTheOldNamesPackageFollowsTheMainOne:

    def test_its_name_and_its_command(self):
        assert OLD_META["name"] == "qualcoder-mcp"
        assert OLD_META["scripts"] == {
            "qualcoder-mcp": "qualcoder_mcp.server:main"}

    def test_the_same_version(self):
        assert Version(OLD_META["version"]) == Version(MAIN_META["version"])

    def test_one_dependency_a_floor_at_that_version(self):
        (only,) = OLD_META["dependencies"]
        requirement = Requirement(only)
        assert requirement.name == "exegete"
        (spec,) = requirement.specifier
        assert spec.operator == ">="
        assert Version(spec.version) == Version(MAIN_META["version"])
        # the PEP 440 form, which names a pre-release, so that pip and uv
        # accept a pre-release of exegete for it
        assert spec.version == str(Version(MAIN_META["version"]))

    def test_the_same_licence_and_the_same_files(self):
        assert OLD_META["license"] == MAIN_META["license"]
        assert OLD_META["license-files"] == MAIN_META["license-files"]
        for name in MAIN_META["license-files"]:
            assert (OLD / name).read_bytes() == (REPO / name).read_bytes(), \
                name

    def test_the_same_python_and_author(self):
        assert OLD_META["requires-python"] == MAIN_META["requires-python"]
        assert OLD_META["authors"] == MAIN_META["authors"]

    def test_its_page_on_pypi_says_where_to_go(self):
        text = (OLD / OLD_META["readme"]).read_text(encoding="utf-8")
        assert text.startswith("# qualcoder-mcp is now Exegete\n")
        for words in ("`exegete`", "https://pypi.org/project/exegete/",
                      "pip install --upgrade qualcoder-mcp",
                      "until version 1.0"):
            assert words in text, words
        assert "—" not in text


class TestTheStandInIsOneFileSet:

    def test_the_same_two_files_in_both_places(self):
        source = REPO / "src" / "qualcoder_mcp"
        copy = OLD / "src" / "qualcoder_mcp"
        for folder in (source, copy):
            assert sorted(p.name for p in folder.iterdir()
                          if p.name != "__pycache__") == sorted(STAND_IN)
        for name in STAND_IN:
            assert (copy / name).read_bytes() == \
                (source / name).read_bytes(), name

    def test_it_calls_the_promised_entry_point(self):
        text = (REPO / "src" / "qualcoder_mcp" / "server.py").read_text(
            encoding="utf-8")
        assert "from exegete.server import main as _main" in text
        assert 'started_as="qualcoder-mcp"' in text
        assert 'if __name__ == "__main__":' in text


class TestTheExegeteBuildsLeaveItOut:

    def test_pyproject_excludes_it(self):
        find = _toml(REPO / "pyproject.toml")["tool"]["setuptools"][
            "packages"]["find"]
        assert find["where"] == ["src"]
        assert set(find["exclude"]) == {"qualcoder_mcp", "qualcoder_mcp.*"}

    def test_manifest_prunes_it(self):
        lines = (REPO / "MANIFEST.in").read_text(
            encoding="utf-8").splitlines()
        assert "prune src/qualcoder_mcp" in lines


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    rh.need_setuptools()
    return rh.build_both(tmp_path_factory.mktemp("builds"))


def _wheel(files):
    (wheel,) = [f for f in files if f.suffix == ".whl"]
    return wheel


def _entry_points(z):
    (name,) = [n for n in z.namelist()
               if n.endswith(".dist-info/entry_points.txt")]
    return z.read(name).decode("utf-8")


class TestWhatEachWheelHolds:

    def test_exegete_holds_no_old_path_and_no_old_command(self, built):
        with zipfile.ZipFile(_wheel(built["exegete"])) as z:
            names = z.namelist()
            points = _entry_points(z)
        assert not [n for n in names if n.startswith("qualcoder_mcp")]
        assert "exegete/server.py" in names
        assert "exegete/names.py" in names
        assert "exegete = exegete.server:main" in points.splitlines()
        assert "qualcoder-mcp" not in points
        assert "qualcoder_mcp" not in points

    def test_the_exegete_sdist_holds_no_stand_in(self, built):
        (sdist,) = [f for f in built["exegete"] if f.name.endswith(".tar.gz")]
        with tarfile.open(sdist) as t:
            names = t.getnames()
        assert not [n for n in names if "qualcoder_mcp/" in n
                    or "pypi-old-name" in n]
        assert any(n.endswith("src/exegete/server.py") for n in names)

    def test_the_old_names_wheel_holds_only_the_stand_in(self, built):
        with zipfile.ZipFile(_wheel(built["old"])) as z:
            names = z.namelist()
            points = _entry_points(z)
            (meta,) = [n for n in names if n.endswith(".dist-info/METADATA")]
            metadata = z.read(meta).decode("utf-8")
        code = sorted(n for n in names if ".dist-info/" not in n)
        assert code == [f"qualcoder_mcp/{f}" for f in sorted(STAND_IN)]
        assert "qualcoder-mcp = qualcoder_mcp.server:main" in \
            points.splitlines()
        version = str(Version(MAIN_META["version"]))
        assert f"Version: {version}" in metadata.splitlines()
        requires = [line for line in metadata.splitlines()
                    if line.startswith("Requires-Dist:")]
        assert requires == [f"Requires-Dist: exegete>={version}"]
        assert Path(_wheel(built["old"])).name.startswith(
            f"qualcoder_mcp-{version}-")
