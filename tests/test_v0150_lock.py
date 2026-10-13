# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the library lock refreshed.

`uv.lock` is what the Claude Desktop extension installs from (the build
copies it into the package and the app runs `uv run --frozen` on it), so
the versions it records are the versions a researcher's computer gets.
These tests pin what the refresh of 13 October 2026 brought:

- each library that carried an advisory on 12 October is at or above the
  release that fixed it;
- PyMuPDF, EbookLib and lxml stay at the releases the import parity
  record names, so PDFs and EPUBs are read as before;
- every package comes from PyPI, apart from Exegete itself;
- starting Exegete and setting up its tools loads neither pyjwt nor
  cryptography (both come with the `mcp` library), so a scanner's flag on
  the cryptography releases kept for Intel Macs and Windows on Arm
  concerns code Exegete does not load at start-up.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server             # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

with open(REPO / "pyproject.toml", "rb") as _handle:
    PYPROJECT = tomllib.load(_handle)
ROOT = PYPROJECT["project"]["name"]
PARITY = json.loads((REPO / "tests" / "fixtures" / "import_expected.json")
                    .read_text(encoding="utf-8"))["versions"]

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

# The readers the import parity gate compares against QualCoder 4.0.
PARITY_LIBRARIES = ("pymupdf", "ebooklib", "lxml")


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


class TestThePDFAndEPUBReadersStay:

    @pytest.mark.parametrize("name", PARITY_LIBRARIES)
    def test_the_release_the_parity_record_names(self, name):
        assert _versions(_lock(), name) == [PARITY[name]]


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


def _child_env(home):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QUALCODER", "EXEGETE"))}
    temp = str(home / "tmp")
    env.update({"PYTHONPATH": str(REPO / "src"), "HOME": str(home),
                "USERPROFILE": str(home), "TMPDIR": temp, "TEMP": temp,
                "TMP": temp, "PYTHONDONTWRITEBYTECODE": "1"})
    return env


# Run in a fresh interpreter: what Exegete loads when it starts and sets up
# a tool set, and whether the two libraries are there to be loaded at all
# (if they were not, their absence would prove nothing).
LOADED = """
import importlib.util, json, sys
import exegete.server as server
server._apply_toolset(sys.argv[1])
print(json.dumps({
    "installed": [n for n in ("jwt", "cryptography")
                  if importlib.util.find_spec(n) is not None],
    "loaded": sorted(m for m in sys.modules
                     if m.split(".")[0] in ("jwt", "cryptography")),
}))
"""


class TestStartingLoadsNeitherLibrary:

    @pytest.mark.parametrize("mode", server._VALID_TOOLSET_MODES)
    def test_neither_is_loaded(self, tmp_path, mode):
        home = tmp_path / "home"
        (home / "tmp").mkdir(parents=True)
        proc = subprocess.run(
            [sys.executable, "-B", "-c", LOADED, mode],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", env=_child_env(home), timeout=120)
        assert proc.returncode == 0, proc.stderr
        answer = json.loads(proc.stdout.strip().splitlines()[-1])
        assert answer["installed"] == ["jwt", "cryptography"]
        assert answer["loaded"] == []

    def test_every_mode_is_covered(self):
        assert set(server._VALID_TOOLSET_MODES) >= {"full", "core",
                                                    "lifecycle"}
