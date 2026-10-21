# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the library lock refreshed.

`uv.lock` is what the Claude Desktop extension installs from (the build
copies it into the package and the app runs `uv run --frozen` on it), so
the versions it records are the versions a researcher's computer gets.
These tests pin what the refresh of 13 October 2026 brought:

- each library that carried an advisory on 12 October is at or above the
  release that fixed it;
- the five reader libraries the import parity record names (PyMuPDF,
  EbookLib, lxml, striprtf and charset-normalizer) stay at its releases,
  so PDFs, EPUBs, RTF and plain-text files are read as the record has
  them;
- every package comes from PyPI, apart from Exegete itself;
- a real start of Exegete (its `main()`, which sets up its tools,
  settles the state folder, tidies and runs the stdio loop) loads neither
  pyjwt nor cryptography (both come with the `mcp` library), so a
  scanner's flag on the cryptography releases kept for Intel Macs and
  Windows on Arm concerns code Exegete does not load at start-up;
- PyMuPDF held below 2 in the optional part `pdf-epub` (the lead's
  decision for 0.15.0, 19 October 2026): CI's suite installs with pip,
  not from the lock, and had begun to get PyMuPDF 2.0, which brings
  libraries of its own and had not been looked at, while the lock and
  the parity record held 1.28.2. From v0.15.1 (the owner's ruling of 21
  October 2026) the part names PyMuPDF in two lines, 1.x and 2.x, each
  bounded below its next major release, the lock records the same two,
  and its releases are those the parity record names (1.28.2, and 2.0
  among the releases giving the same text); a real start loads neither
  PyMuPDF nor the libraries PyMuPDF 2 brings.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server             # noqa: E402

sys.path.insert(0, str(REPO / "tests"))
import import_fixtures                       # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

with open(REPO / "pyproject.toml", "rb") as _handle:
    PYPROJECT = tomllib.load(_handle)
ROOT = PYPROJECT["project"]["name"]
RECORD = json.loads((REPO / "tests" / "fixtures" / "import_expected.json")
                    .read_text(encoding="utf-8"))
PARITY = RECORD["versions"]

PYPI_INDEX = "https://pypi.org/simple"
PYPI_FILES = "https://files.pythonhosted.org/packages/"

# The release that fixed the advisories OSV listed against each library on
# 12 October 2026, before the refresh (each GHSA has a PYSEC twin).
FIXED_IN = {
    "pyjwt": "2.15.0",             # GHSA-42vr-xj54-vc7v, GHSA-x33g-cr3x-6449
    "starlette": "1.3.1",          # five, the last fixed in 1.3.1
    "python-multipart": "0.0.31",  # seven, the last fixed in 0.0.31
    "anyio": "4.14.2",             # GHSA-5p39-cfhj-2xmp, GHSA-82r6-8w77-94w6
    "idna": "3.15",                # GHSA-65pc-fj4g-8rjx
    "python-dotenv": "1.2.2",      # GHSA-mf9w-mj56-hr94
    "pytest": "9.0.3",             # GHSA-6w46-j5rx-g56g (development only)
    "pygments": "2.20.0",          # GHSA-5239-wwwm-4pmq (development only)
}

# The readers the import parity gate compares against QualCoder 4.0: every
# library the parity record names a version for, so that a later refresh
# cannot move one of them with every test green.
PARITY_LIBRARIES = ("pymupdf", "ebooklib", "lxml", "striprtf",
                    "charset-normalizer")


def _lock():
    with open(REPO / "uv.lock", "rb") as handle:
        return tomllib.load(handle)


def _versions(lock, name):
    return [p["version"] for p in lock["package"] if p["name"] == name]


def not_from_pypi(lock, root):
    """Every way an entry departs from PyPI, as (name, version, what):
    a source other than PyPI's index, or a file not on PyPI's file host.
    The project itself, `root`, is the one entry allowed to be editable."""
    found = []
    for package in lock["package"]:
        name, version = package["name"], package.get("version")
        source = package.get("source", {})
        if name == root and source == {"editable": "."}:
            continue
        if source != {"registry": PYPI_INDEX}:
            found.append((name, version, f"source {source}"))
        files = ([package["sdist"]] if "sdist" in package else []) + \
            package.get("wheels", [])
        for entry in files:
            url = entry.get("url", "")
            if not url.startswith(PYPI_FILES):
                found.append((name, version, f"file {url or entry}"))
    return found


class TestTheAdvisoriesAreCleared:

    @pytest.mark.parametrize("name", sorted(FIXED_IN))
    def test_at_or_above_the_release_that_fixed_it(self, name):
        versions = _versions(_lock(), name)
        assert versions, f"{name} is no longer in the lock"
        for version in versions:
            assert Version(version) >= Version(FIXED_IN[name]), \
                f"{name} {version} is below {FIXED_IN[name]}"


class TestTheReadersStay:

    @pytest.mark.parametrize("name", PARITY_LIBRARIES)
    def test_the_release_the_parity_record_names(self, name):
        """The record's release, and for PyMuPDF the releases it lists as
        giving QualCoder's functions the same text (v0.15.1)."""
        named = [PARITY[name]] + RECORD.get("same_text_with", {}).get(
            name, [])
        assert sorted(_versions(_lock(), name), key=Version) == \
            sorted(named, key=Version)

    def test_every_library_the_record_names_is_guarded(self):
        """A library the record gains later is guarded as well."""
        assert set(PARITY) - {"python"} == set(PARITY_LIBRARIES)


class TestEveryPackageComesFromPyPI:

    def test_nothing_but_the_project_departs_from_pypi(self):
        assert not_from_pypi(_lock(), ROOT) == []

    def test_the_project_is_the_editable_entry(self):
        ours = [p for p in _lock()["package"] if p["name"] == ROOT]
        assert [p["source"] for p in ours] == [{"editable": "."}]

    def test_the_check_finds_a_departure(self):
        """A doctored lock: one entry from another index, one from git, a
        wheel and an sdist on another host, and a second editable entry."""
        here = {"registry": PYPI_INDEX}
        good = PYPI_FILES + "aa/bb/a-1-py3-none-any.whl"
        lock = {"package": [
            {"name": "root", "version": "1", "source": {"editable": "."}},
            {"name": "fine", "version": "1", "source": here,
             "sdist": {"url": PYPI_FILES + "aa/bb/fine-1.tar.gz"},
             "wheels": [{"url": good}]},
            {"name": "mirror", "version": "2",
             "source": {"registry": "https://mirror.example/simple"},
             "wheels": [{"url": good}]},
            {"name": "fromgit", "version": "3",
             "source": {"git": "https://example.org/x.git"}},
            {"name": "elsewhere", "version": "4", "source": here,
             "sdist": {"url": "https://example.org/elsewhere-4.tar.gz"},
             "wheels": [{"url": "https://example.org/e-4-py3-none-any.whl"}]},
            {"name": "other", "version": "5", "source": {"editable": "."}},
        ]}
        found = not_from_pypi(lock, "root")
        assert [(name, version) for name, version, _ in found] == [
            ("mirror", "2"), ("fromgit", "3"), ("elsewhere", "4"),
            ("elsewhere", "4"), ("other", "5")]
        assert not_from_pypi({"package": lock["package"][:2]}, "root") == []


def _extra_pymupdf():
    """PyMuPDF's lines in the optional part `pdf-epub`, in their order:
    1.x, then 2.x (v0.15.1)."""
    found = [Requirement(line) for line in
             PYPROJECT["project"]["optional-dependencies"]["pdf-epub"]
             if Requirement(line).name == "pymupdf"]
    assert len(found) == 2, found
    return found


class TestPyMuPDFInTwoLines:

    def test_each_line_keeps_below_its_next_major(self):
        first, second = (line.specifier for line in _extra_pymupdf())
        # 1.x: from the floor that fixed PyMuPDF's advisory, below 2
        for release in ("1.26.7", "1.28.2", PARITY["pymupdf"]):
            assert first.contains(release), release
        for release in ("1.26.6", "2.0", "2.0.1", "2.1"):
            assert not first.contains(release), release
        # 2.x: from 2.0, below 3
        for release in ("2.0", "2.1"):
            assert second.contains(release), release
        for release in ("1.28.2", "3.0"):
            assert not second.contains(release), release

    def test_the_lock_records_the_same_two(self):
        """`uv lock --check` compares these. uv rewrites each line's
        marker (python_full_version, reordered, joined with the extra),
        so the markers are compared by what they decide over the grid
        of computers and Pythons, not as text; each locked release keeps
        within its line."""
        from test_v0151_pymupdf_two import grid, marker_environment
        lock = _lock()
        ours = [p for p in lock["package"] if p["name"] == ROOT]
        locked = [d for d in ours[0]["metadata"]["requires-dist"]
                  if d["name"] == "pymupdf"]
        lines = _extra_pymupdf()
        assert sorted(str(SpecifierSet(d["specifier"])) for d in locked) \
            == sorted(str(line.specifier) for line in lines)
        for line in lines:
            entry = next(d for d in locked
                         if SpecifierSet(d["specifier"]) == line.specifier)
            for point in grid():
                for extra in ("pdf-epub", ""):
                    env = marker_environment(*point, extra=extra)
                    assert Marker(entry["marker"]).evaluate(env) == (
                        bool(extra) and line.marker.evaluate(env)), \
                        (str(line.specifier), point, extra)
        for version in _versions(lock, "pymupdf"):
            assert sum(line.specifier.contains(version)
                       for line in lines) == 1, version

    def test_the_changelog_says_so(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        entry = " ".join(text[text.index("## [0.15.0-alpha]"):
                              text.index("## [0.14.3-alpha]")].split())
        assert ("PDF reading is held to PyMuPDF 1.x for now on every route, "
                "installs from PyPI included (the optional part `pdf-epub` "
                "asks for a release below 2), with PyMuPDF 2.0 to be looked "
                "at in a later release.") in entry


def _child_env(home, mode):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QUALCODER", "EXEGETE"))}
    temp = str(home / "tmp")
    env.update({"PYTHONPATH": str(REPO / "src"), "HOME": str(home),
                "USERPROFILE": str(home), "TMPDIR": temp, "TEMP": temp,
                "TMP": temp, "PYTHONDONTWRITEBYTECODE": "1",
                # A start tidies the reading folder: under `home` on Linux
                # and Windows too (on a Mac it is under HOME already)
                "XDG_CACHE_HOME": str(home / "cache"),
                "LOCALAPPDATA": str(home / "localappdata"),
                "EXEGETE_TOOLSET": mode, "EXEGETE_UPDATE_CHECK": "off"})
    return env


# Run in a fresh interpreter: a real start of Exegete, `main()` as the
# `exegete` command runs it. It reads the tool set from its setting and
# sets it up, settles the state folder, tidies the reading folder and the
# kept texts, sets up the check for new versions (switched off here, so
# nothing is fetched) and runs the stdio loop, which stops at once on an
# empty input. What is loaded is read at exit, after all of that, and
# written to a file rather than printed, since the stdio loop takes over
# standard output. With it, whether the libraries are there to be
# loaded at all (if they were not, their absence would prove nothing).
# v0.15.1: PyMuPDF too (under either of its names), and onnxruntime and
# numpy, which PyMuPDF 2 brings and loads; a start loads none of them.
WATCHED = ("jwt", "cryptography", "pymupdf", "fitz", "onnxruntime", "numpy")
STARTED = """
import atexit, importlib.util, json, sys
report = sys.argv[1]
watched = %r
seen = {"returned": False}

def write():
    seen["installed"] = [n for n in watched
                         if importlib.util.find_spec(n) is not None]
    seen["loaded"] = sorted(m for m in sys.modules
                            if m.split(".")[0] in watched)
    with open(report, "w", encoding="utf-8") as handle:
        json.dump(seen, handle)

atexit.register(write)
sys.argv = ["exegete"]
import exegete.server as server
seen["mode"] = server._resolve_toolset_mode()
server.main()
seen["returned"] = True
""" % (WATCHED,)


class TestStartingLoadsNeitherLibrary:

    @pytest.mark.parametrize("mode", server._VALID_TOOLSET_MODES)
    def test_neither_is_loaded(self, tmp_path, mode):
        home = tmp_path / "home"
        (home / "tmp").mkdir(parents=True)
        report = tmp_path / "loaded.json"
        proc = subprocess.run(
            [sys.executable, "-B", "-c", STARTED, str(report)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", env=_child_env(home, mode), timeout=120)
        assert proc.returncode == 0, proc.stderr
        answer = json.loads(report.read_text(encoding="utf-8"))
        assert answer["mode"] == mode
        assert answer["returned"], proc.stderr
        installed = set(answer["installed"])
        assert {"jwt", "cryptography"} <= installed
        # PyMuPDF wherever the optional part is installed, and the
        # libraries PyMuPDF 2 brings wherever its line applies, so that
        # the check is not empty there (on Python 3.10 and on Macs,
        # PyMuPDF alone is checked)
        if import_fixtures.optional_part_installed():
            assert "pymupdf" in installed
            if _extra_pymupdf()[1].marker.evaluate():
                assert {"onnxruntime", "numpy"} <= installed
        assert answer["loaded"] == [], proc.stderr

    def test_every_mode_is_covered(self):
        # v0.15.0: two sets (names.TOOLSETS); `lifecycle` is read as `full`
        from exegete import names
        assert server._VALID_TOOLSET_MODES == names.TOOLSETS
        assert set(names.TOOLSETS) == {"full", "core"}
        assert set(names.OLD_TOOLSET_NAMES.values()) <= set(names.TOOLSETS)
