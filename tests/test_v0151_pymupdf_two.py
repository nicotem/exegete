# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: PyMuPDF 2.0 where it has ready-made packages (the owner's
ruling of 21 October 2026), with a larger memory cap for PDFs.

- The optional part `pdf-epub` names PyMuPDF in two lines: 2.x on
  Windows x64 and Linux (x86-64 and Arm) with Python 3.11 to 3.14, 1.x
  everywhere else, each line the exact complement of the other, so every
  computer takes one; neither reads the system's release.
- The lock agrees: its walk from the project with the part reaches 2.0
  on those three computers and 1.28.2 on the other three, at each
  Python; uv is told never to build PyMuPDF.
- A PDF's reading is given 2 GiB, every other kind 1 GiB, and a PDF
  refused for memory names the cap that applied. On Linux the reading
  process starts with three fixed settings, and a child started as it
  is, under the PDF cap, reads a PDF with room to spare.
- onnxruntime's usage reports, on by default, are switched off in the
  reading process: its setting on every system (Linux and macOS heed
  it), and its own switch before PyMuPDF loads (Windows heeds that
  alone); a reading with 2.0 keeps nothing in a home it is given.
- Where psutil is installed (it comes with PyMuPDF 2), the check for a
  running QualCoder goes through it and reads command lines.
- NOTICE names every library PyMuPDF 2 brings, with its licence; the
  advisory check asks OSV about each locked release.
"""

import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import time
import types
from importlib import metadata
from pathlib import Path

import pytest
from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import check_advisories  # noqa: E402
import import_fixtures  # noqa: E402
from exegete import database, doc_import, env_settings  # noqa: E402
from exegete import import_reading  # noqa: E402
from test_v014_desktop_extension import ENVIRONMENTS, lock_walk_releases  # noqa: E402,E501

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

with open(REPO / "pyproject.toml", "rb") as _handle:
    PYPROJECT = tomllib.load(_handle)
ROOT = PYPROJECT["project"]["name"]
OPTIONAL = import_fixtures.optional_part_installed()

# The markers' grid: every system, processor and Python the lines must
# divide between them, the computers Exegete supports and some it does
# not (FreeBSD, 32-bit x86).
SYSTEMS = ("darwin", "win32", "linux", "freebsd")
MACHINES = ("arm64", "x86_64", "AMD64", "ARM64", "aarch64", "x86")
PYTHONS = ("3.10", "3.11", "3.12", "3.13", "3.14", "3.15")
# Where the second line, PyMuPDF 2, applies: these, Python 3.11 to 3.14.
# Windows x64 twice: "AMD64" as Windows' own Python names its processor,
# "x86_64" as uv does when asked about Windows x64 from another computer
# (CI's dry run, whose table and wheel check must see what Windows sees).
TWO_X = {("win32", "AMD64"), ("win32", "x86_64"), ("linux", "x86_64"),
         ("linux", "aarch64")}
TWO_X_PYTHONS = ("3.11", "3.12", "3.13", "3.14")
FIRST, SECOND = "1.28.2", "2.0"


def marker_environment(system, machine, python, extra=""):
    return {
        "sys_platform": system, "platform_machine": machine,
        "python_version": python, "python_full_version": f"{python}.0",
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
        "os_name": "nt" if system == "win32" else "posix",
        "platform_system": {"darwin": "Darwin", "win32": "Windows",
                            "linux": "Linux"}.get(system, "FreeBSD"),
        "platform_release": "", "platform_version": "", "extra": extra,
    }


def grid():
    return [(system, machine, python) for system in SYSTEMS
            for machine in MACHINES for python in PYTHONS]


def pymupdf_lines(project=None):
    """PyMuPDF's lines in the optional part, in their order."""
    project = project or PYPROJECT["project"]
    return [Requirement(line)
            for line in project["optional-dependencies"]["pdf-epub"]
            if Requirement(line).name == "pymupdf"]


def lines_taken(lines, system, machine, python):
    """The indices of the lines that apply on that computer."""
    env = marker_environment(system, machine, python)
    return [index for index, line in enumerate(lines)
            if line.marker is None or line.marker.evaluate(env)]


def two_x_applies(system, machine, python):
    return (system, machine) in TWO_X and python in TWO_X_PYTHONS


def _lock():
    with open(REPO / "uv.lock", "rb") as handle:
        return tomllib.load(handle)


# ---------------------------------------------------------------------------
# The two lines
# ---------------------------------------------------------------------------

class TestTheTwoLines:

    def test_two_lines_the_second_for_pymupdf_2(self):
        first, second = pymupdf_lines()
        assert first.specifier == SpecifierSet(">=1.26.7,<2")
        assert second.specifier == SpecifierSet(">=2.0,<3")

    def test_every_computer_takes_exactly_one(self):
        lines = pymupdf_lines()
        for system, machine, python in grid():
            assert len(lines_taken(lines, system, machine, python)) == 1, \
                (system, machine, python)

    def test_the_second_exactly_where_pymupdf_2_has_packages(self):
        lines = pymupdf_lines()
        for system, machine, python in grid():
            wanted = [1] if two_x_applies(system, machine, python) else [0]
            assert lines_taken(lines, system, machine, python) == wanted, \
                (system, machine, python)

    def test_neither_reads_the_systems_release(self):
        for line in pymupdf_lines():
            for name in ("platform_release", "platform_version"):
                assert name not in str(line.marker), line

    def test_uv_never_builds_pymupdf(self):
        assert "pymupdf" in PYPROJECT["tool"]["uv"]["no-build-package"]


class TestTheLockAgrees:

    # Each Python the lock is made for: from 0.15.2, 3.11 or newer
    # (pyproject.toml's requires-python), so the lock holds no walk for
    # 3.10, which the markers above still give a line of its own.
    @pytest.mark.parametrize("python", ["3.11", "3.12", "3.13", "3.14"])
    def test_the_walk_reaches_the_release_each_line_names(self, python):
        lock = _lock()
        for system, machine in ENVIRONMENTS:
            reached = lock_walk_releases(lock, ROOT, system, machine,
                                         root_extras=("pdf-epub",),
                                         python=python)
            wanted = SECOND if two_x_applies(system, machine, python) \
                else FIRST
            assert reached["pymupdf"] == wanted, (system, machine, python)

    def test_at_the_extensions_python_three_computers_each(self):
        lock = _lock()
        found = {}
        for system, machine in ENVIRONMENTS:
            found[(system, machine)] = lock_walk_releases(
                lock, ROOT, system, machine, root_extras=("pdf-epub",),
                python="3.13")["pymupdf"]
        # the six computers by their own Pythons' names (Windows x64 as
        # "AMD64")
        assert {k for k, v in found.items() if v == SECOND} \
            == TWO_X & set(ENVIRONMENTS)
        assert sorted(found.values()) == [FIRST] * 3 + [SECOND] * 3

    def test_the_locked_releases_are_exactly_the_two(self):
        assert sorted(p["version"] for p in _lock()["package"]
                      if p["name"] == "pymupdf") == [FIRST, SECOND]


# ---------------------------------------------------------------------------
# The cap, and the reading process's environment
# ---------------------------------------------------------------------------

GIB = 1024 * 1024 * 1024


def test_a_pdf_is_given_2_gib_and_every_other_kind_1():
    assert import_reading.PDF_MEMORY_CAP_BYTES == 2 * GIB
    assert import_reading.MEMORY_CAP_BYTES == GIB
    assert import_reading.memory_cap_for("pdf") == 2 * GIB
    for kind in ("word", "opendocument", "rtf", "text", "markdown",
                 "web page", "subtitles", "epub"):
        assert import_reading.memory_cap_for(kind) == GIB, kind


@pytest.mark.parametrize("kind, cap", [("pdf", 2 * GIB), ("word", GIB)])
def test_the_reading_is_started_with_its_kinds_cap(monkeypatch, kind, cap):
    """What read_in_process hands the reading process and its watch,
    when no cap is passed: the header's figure and the cap the watch
    (macOS) or the job object (Windows) enforces."""
    seen = {}

    def talk(process, payload, timeout, memory_cap, kind=None):
        process.kill()
        process.wait()
        seen["header"] = json.loads(payload.split(b"\n", 1)[0])
        seen["cap"] = memory_cap
        return {"text": ""}

    monkeypatch.setattr(import_reading, "_talk", talk)
    import_reading.read_in_process(kind, b"%PDF-1.4")
    assert seen["header"]["memory"] == cap
    assert seen["cap"] == cap


def _refused_for_memory(name, kind):
    item = doc_import.Item(order=1, given=1, path=Path(name),
                           disk_name=name, kind=kind,
                           position="the file given as path 1", name=name)

    def reader(kind, data, max_characters=0, timeout=None):
        raise import_reading.ReadFailed("reader_memory")
    ctx = doc_import.Context(project_folder=Path("."), source_names={},
                             documents_listing=[], refused_places=[],
                             reader=reader)
    doc_import._read_one(item, b"data", ctx)
    return item


@pytest.mark.parametrize("name, kind, figure", [
    ("a.pdf", "pdf", 2048), ("a.docx", "word", 1024),
    ("a.epub", "epub", 1024)])
def test_a_memory_refusal_names_the_cap_that_applied(name, kind, figure):
    item = _refused_for_memory(name, kind)
    assert item.code == "reader_memory"
    assert item.numbers["limit_mb"] == figure
    assert f"({figure} MB)" in doc_import.refusal_words(item)


LINUX_SETTINGS = {"MALLOC_ARENA_MAX": "2", "OPENBLAS_NUM_THREADS": "1",
                  "OMP_NUM_THREADS": "1"}


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_three_fixed_settings_on_linux_alone(monkeypatch, platform):
    """Fixed, never the host's: a host value of its own is not taken."""
    for key in LINUX_SETTINGS:
        monkeypatch.setenv(key, "64")
    monkeypatch.setattr(sys, "platform", platform)
    env = env_settings.reader_process_environment()
    added = {key: env[key] for key in LINUX_SETTINGS if key in env}
    assert added == (LINUX_SETTINGS if platform == "linux" else {})
    assert env_settings.READER_LINUX_SETTINGS == LINUX_SETTINGS


# ---------------------------------------------------------------------------
# onnxruntime's usage reports, which PyMuPDF 2 brings, switched off
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_onnxruntimes_reports_are_switched_off_on_every_system(
        monkeypatch, platform):
    """Fixed, never the host's: a host that sets it otherwise is not
    followed."""
    monkeypatch.setenv("ORT_DISABLE_TELEMETRY", "0")
    monkeypatch.setattr(sys, "platform", platform)
    env = env_settings.reader_process_environment()
    assert env["ORT_DISABLE_TELEMETRY"] == "1"
    assert env_settings.READER_SETTINGS == {"ORT_DISABLE_TELEMETRY": "1"}


class _Watch(importlib.abc.MetaPathFinder):
    """Notes PyMuPDF's import, and keeps the real one out; with
    `onnxruntime_too`, notes and keeps out onnxruntime's as well."""

    def __init__(self, seen, onnxruntime_too=False):
        self.seen = seen
        self.kept_out = ("pymupdf", "onnxruntime") if onnxruntime_too \
            else ("pymupdf",)

    def find_spec(self, name, path=None, target=None):
        if name in self.kept_out:
            self.seen.append(name)
            raise ImportError("kept out by the test")
        return None


def _pymupdf_installed_as(monkeypatch, release):
    """The PyMuPDF release the reading process finds installed, whatever
    this computer has (None: not installed)."""
    real = metadata.version

    def version(name):
        if name.lower() != "pymupdf":
            return real(name)
        if release is None:
            raise metadata.PackageNotFoundError(name)
        return release
    monkeypatch.setattr(metadata, "version", version)


def _a_reading_watched(monkeypatch, kind, data, release="2.0.0"):
    """`_read` in this process, with an onnxruntime of the test's own
    whose switch notes its call, PyMuPDF `release` installed, and
    PyMuPDF's import noted: what happened, in order."""
    seen = []
    fake = types.ModuleType("onnxruntime")
    fake.__spec__ = importlib.machinery.ModuleSpec("onnxruntime", None)
    fake.disable_telemetry_events = lambda: seen.append("switched off")
    monkeypatch.setitem(sys.modules, "onnxruntime", fake)
    for name in [name for name in sys.modules
                 if name == "pymupdf" or name.startswith("pymupdf.")]:
        monkeypatch.delitem(sys.modules, name)
    _pymupdf_installed_as(monkeypatch, release)
    monkeypatch.setattr(sys, "meta_path", [_Watch(seen)] + sys.meta_path)
    answer = import_reading._read({"kind": kind, "size": len(data)}, data)
    return seen, answer


def test_a_pdfs_reading_switches_onnxruntimes_reports_off_before_pymupdf(
        monkeypatch):
    """On Windows, onnxruntime's own switch is the only one its reports
    heed; PyMuPDF 2 starts onnxruntime's models as it is imported."""
    seen, answer = _a_reading_watched(monkeypatch, "pdf", b"%PDF-1.4")
    assert seen == ["switched off", "pymupdf"]
    assert answer["ok"] is False      # PyMuPDF kept out: refused


def test_no_other_kind_of_file_loads_onnxruntime(monkeypatch):
    seen, _answer = _a_reading_watched(monkeypatch, "word", b"PK not a docx")
    assert seen == []


# (the combined review's second round, 21 October 2026) PyMuPDF 1.x never
# loads onnxruntime: loading it there, where it is installed beside 1.x
# for some other reason, would only bring its Windows report.
@pytest.mark.parametrize("release, loaded", [
    ("2.0.0", True), ("2.1.3", True), ("10.0", True),
    ("an unreadable release", True),
    ("1.28.2", False), ("1.26.5", False), (None, False)])
def test_onnxruntime_is_loaded_only_where_pymupdf_2_or_later_is(
        monkeypatch, release, loaded):
    seen = []
    monkeypatch.delitem(sys.modules, "onnxruntime", raising=False)
    for name in [name for name in sys.modules
                 if name == "pymupdf" or name.startswith("pymupdf.")]:
        monkeypatch.delitem(sys.modules, name)
    _pymupdf_installed_as(monkeypatch, release)
    monkeypatch.setattr(sys, "meta_path",
                        [_Watch(seen, onnxruntime_too=True)] + sys.meta_path)
    data = b"%PDF-1.4"
    answer = import_reading._read({"kind": "pdf", "size": len(data)}, data)
    assert seen == (["onnxruntime", "pymupdf"] if loaded else ["pymupdf"])
    assert answer["ok"] is False      # PyMuPDF kept out: refused


@pytest.mark.skipif(not OPTIONAL, reason="PyMuPDF needed")
def test_the_installed_pymupdf_is_read_by_its_own_release():
    """The release read where the reading process looks it up is the one
    that loads: 2.0 in CI's Ubuntu and Windows 3.13, 1.28.2 elsewhere."""
    import pymupdf
    major = int(pymupdf.__version__.split(".", 1)[0])
    assert import_reading._pymupdf_loads_onnxruntime() is (major >= 2)


def _flat_section(name, heading):
    text = (REPO / name).read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    return " ".join(text[start:end if end > 0 else None].split())


def test_privacy_says_what_onnxruntime_reports_and_what_can_be_done():
    """The owner's ruling 96 (22 October 2026): Exegete has no telemetry
    of its own; PRIVACY names onnxruntime's reports where it says what
    stays on the computer and who else reads it: on Linux switched off
    before it loads, nothing kept; on Windows a few reports to Windows'
    diagnostic data each time a PDF is read, under the computer's
    setting; the switch's limits; what a researcher can do. The words
    round after the privacy reader's check (ruling 97): onnxruntime
    1.31.0 writes ProcessInfo, then RegisterEpLibraryStart, a DriverInfo
    event for the graphics adapters and one for any NPU, and
    RegisterEpLibraryEnd before its switch can be reached (environment.cc
    397 to 403, windows/device_discovery.cc 119 to 330, windows/telemetry.cc
    757 to 773 and 927 to 968); the part is the second question, what
    Microsoft can learn about the library's use, with no participant
    data; and the four passages that say nothing else leaves point to
    it."""
    flows = _flat_section("PRIVACY.md", "## How your data flows")
    # (v0.15.2, the lead's reading: the section's first paragraph names the
    # systems the summary names, Windows x64, where the library reports,
    # and Linux, where Exegete's setting stops it before it starts)
    assert ("no telemetry, no analytics, and no separate cloud path** of "
            "its own. On Windows x64, a library Exegete installs to read "
            "PDFs reports its use to Windows' diagnostic data each time a "
            "PDF is read, with nothing from your documents.") in flows
    assert ("Exegete switches its reports off: on Linux before the library "
            "starts, so it reports nothing there, and on Windows once it "
            "has loaded, after its first few reports") in flows
    # (the fix round: "nothing there" holds for the release the lock
    # gives, so the pointer names the switch's limits, which say so)
    assert ("\"A library's usage reports\", below, says what they hold, "
            "the switch's limits, and what you can do.") in flows
    assert ("Another release of onnxruntime, installed other than through "
            "Exegete's lock, may treat the setting and the switch "
            "differently.") in flows
    summary = _flat_section("PRIVACY.md", "## Where your data goes, in "
                            "short")
    assert ("**On Windows x64**, a library Exegete installs to read PDFs "
            "reports its use to Windows' diagnostic data each time a PDF "
            "is read, with nothing from your documents") in summary
    assert "Linux reports" not in flows and "Linux reports" not in summary
    # the two switches those sentences describe: the setting in the
    # reading process's environment, before onnxruntime loads, and
    # onnxruntime's own switch once it has loaded
    import inspect
    assert env_settings.READER_SETTINGS == {"ORT_DISABLE_TELEMETRY": "1"}
    assert "disable_telemetry_events()" in inspect.getsource(
        import_reading._onnxruntime_reports_off)
    start = flows.index("**A library's usage reports (what Microsoft can "
                        "learn about the library being used on this "
                        "computer, with no participant data).**")
    part = flows[start:flows.index("An assistant that opens files by "
                                   "itself", start)]
    for fact in (
            "Exegete switches this off in the process that reads a "
            "document, before onnxruntime loads",
            "`ORT_DISABLE_TELEMETRY`), so nothing is kept and nothing is "
            "sent",
            "by which time it has made a few reports",
            "**each time a PDF is read**",
            "the names and driver versions of the computer's graphics "
            "adapters and of any NPU",
            "that onnxruntime registered its processor part, with any error",
            "Windows adds its own identifiers to what it sends",
            "comes from onnxruntime's source code and the Windows package "
            "Exegete installs (1.31.0)",
            "never anything from your documents or projects",
            "as the computer's diagnostic data setting says",
            "Exegete then switches off every later report in that process",
            "has not been watched on a Windows computer",
            "can switch its reports on again for that reading",
            "you could read no PDFs through Exegete on Windows",
            "what the computer's diagnostic data setting lets Windows "
            "send"):
        assert fact in part, fact
    # and where reading is, no longer "no network" alone
    reading = _flat_section("PRIVACY.md", "## Bringing documents in")
    assert "use no network" not in reading
    assert ("Import and reading make no request over the network of "
            "their own") in reading
    assert ("by then it has made a few reports to Windows' diagnostic "
            "data") in reading
    assert "graphics adapters and of any NPU among them" in reading
    assert "Windows adds its own identifiers to what it sends" in reading
    # the passages that say what else leaves the computer point to the part
    pointer = "a library Exegete installs for PDFs also reports its use"
    assert pointer in " ".join(flows.split())
    # (the fix round: the checklist's question on what Exegete connects
    # to, which says what a data-management plan can state, names them)
    checklist = _flat_section("PRIVACY.md",
                              "## Before you use real participant data")
    connects = checklist[checklist.index("**What Exegete itself connects "
                                         "to.**"):]
    connects = connects[:connects.index(" - **")]
    assert ("On Windows x64, " + pointer + " to Windows' diagnostic data, "
            "with nothing from your documents (\"A library's usage "
            "reports\", under \"How your data flows\").") in connects
    assert connects.index("Windows' diagnostic data") < connects.index(
        "it can say this")
    governance = _flat_section("PRIVACY.md", "## Your governance options")
    assert ("though on Windows x64 a library it installs for PDFs reports "
            "its use to Windows") in governance
    # (v0.15.2: the LM Studio recipe is the Terminal guide's)
    install = " ".join((REPO / "docs/installing-from-the-terminal.md"
                        ).read_text(encoding="utf-8").split())
    assert install.count("library it installs for PDFs reports its use") \
        + install.count("library Exegete installs for PDFs reports its use") \
        == 2
    readme = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    # (v0.15.2, the readability reading: Exegete named, after a sentence
    # whose subject is the check)
    assert ("On Windows x64, a library Exegete installs for PDFs also reports "
            "its use, with nothing from your projects") in readme
    assert "\"A library's usage reports\", under \"How your data flows\"" \
        in reading


def test_the_changelog_names_the_windows_report_among_known_limits():
    """For the release notes' known limits (ruling 96)."""
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = text[text.index("## [0.15.1-alpha]"):
                      text.index("\n## [", text.index("## [0.15.1-alpha]") + 1)]
    start = unreleased.index("\n### Known limits\n")
    limits = " ".join(unreleased[start:unreleased.index(
        "\n### ", start + 1)].split())
    assert ("**On Windows x64, a library Exegete installs for PDFs makes a "
            "few reports of its use to Windows' diagnostic data each time a "
            "PDF is read.**") in limits
    assert ("the names and driver versions of the computer's graphics "
            "adapters and of any NPU") in limits
    assert ("onnxruntime's source code and the Windows package Exegete "
            "installs (1.31.0)") in limits
    assert "you could read no PDFs through Exegete on Windows" in limits
    assert 'PRIVACY.md, "How your data flows", says more' in limits
    # (the second round) 2 GB because PyMuPDF 2 can need more than 1 GB on
    # Linux: CI measured 376 MiB with the reading process's settings
    flat = " ".join(unreleased.split())
    assert "PyMuPDF 2 needs more than the 1 GB" not in flat
    assert ("given 2 GB of memory, since with PyMuPDF 2 it can need more "
            "than 1 GB on Linux") in flat


def test_contributing_says_exegetes_code_imports_onnxruntime():
    """Since fix round 1 Exegete's own code imports onnxruntime, in the
    reading process alone, to switch its reports off."""
    text = " ".join((REPO / "CONTRIBUTING.md").read_text(
        encoding="utf-8").split())
    assert "never by Exegete's own code" not in text
    assert ("loaded only inside the reading process, never at Exegete's "
            "start, where Exegete's own code imports onnxruntime only to "
            "switch its usage reports off") in text


def test_the_parity_script_switches_onnxruntimes_reports_off(tmp_path):
    """Run by a contributor with PyMuPDF 2 outside CI, the script would
    otherwise give onnxruntime a device id, an event store and its
    uploader; a host's own value is not followed."""
    probe = ("import importlib.util, os, sys; "
             "spec = importlib.util.spec_from_file_location("
             "'qualcoder_parity', sys.argv[1]); "
             "module = importlib.util.module_from_spec(spec); "
             "spec.loader.exec_module(module); "
             "print(os.environ.get('ORT_DISABLE_TELEMETRY'))")
    for host in (None, "0"):
        env = {key: value for key, value in os.environ.items()
               if key != "ORT_DISABLE_TELEMETRY"}
        if host is not None:
            env["ORT_DISABLE_TELEMETRY"] = host
        done = subprocess.run(
            [sys.executable, "-c", probe,
             str(REPO / "scripts" / "qualcoder_parity.py")],
            env=env, cwd=tmp_path, capture_output=True, text=True,
            timeout=120)
        assert done.returncode == 0, done.stderr
        assert done.stdout.strip() == "1"


def _onnxruntime_installed():
    return importlib.util.find_spec("onnxruntime") is not None


@pytest.mark.skipif(not OPTIONAL or not _onnxruntime_installed(),
                    reason="PyMuPDF 2 and onnxruntime needed")
def test_a_reading_with_pymupdf_2_keeps_nothing_in_a_home_it_is_given(
        monkeypatch, tmp_path):
    """Given a home (Exegete gives it none, so onnxruntime would find the
    account's own), the reading process keeps nothing there: no
    onnxruntime device id or event store (Linux's .cache, macOS's
    Library/Application Support/Microsoft)."""
    home = tmp_path / "home"
    home.mkdir()
    small = import_reading._small_environment

    def with_a_home():
        env = small()
        env["HOME"] = env["USERPROFILE"] = str(home)
        return env
    monkeypatch.setattr(import_reading, "_small_environment", with_a_home)
    result = import_reading.read_in_process(
        "pdf", import_fixtures.all_fixtures()["three_pages.pdf"])
    assert result["words"] > 0
    assert sorted(str(path.relative_to(home))
                  for path in home.rglob("*")) == []


# A child started as the reading process is (its Python, isolated, the
# small environment, a private folder, bytes on standard input), which
# sets the PDF cap on itself first, reads a PDF and gives the peak of its
# address space, the figure the cap limits on Linux.
PEAK_CHILD = (
    "import json, sys; sys.path.insert(0, sys.argv[1]); "
    "from exegete import import_reading; "
    "import_reading._limit_own_memory(int(sys.argv[2])); "
    "from exegete import doc_readers; "
    "result = doc_readers.read_document('pdf', sys.stdin.buffer.read()); "
    "import pymupdf; "
    "peak = [line.split()[1] for line in open('/proc/self/status') "
    "if line.startswith('VmPeak:')][0]; "
    "print(json.dumps({'words': result['words'], 'peak_kib': int(peak), "
    "'release': pymupdf.__version__}))")


@pytest.mark.skipif(not sys.platform.startswith("linux") or not OPTIONAL,
                    reason="the address-space cap is Linux's; PyMuPDF needed")
def test_a_pdf_is_read_well_within_the_pdf_cap(tmp_path, capsys):
    cap = import_reading.PDF_MEMORY_CAP_BYTES
    command = import_reading.reader_command()
    proc = subprocess.run(
        [command[0], "-I", "-c", PEAK_CHILD, command[-1], str(cap)],
        input=import_fixtures.all_fixtures()["three_pages.pdf"],
        capture_output=True, env=import_reading._small_environment(),
        cwd=str(tmp_path), timeout=120)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[-2000:]
    answer = json.loads(proc.stdout)
    with capsys.disabled():
        print(f"\nreading process peak: {answer['peak_kib'] // 1024} MiB "
              f"of {cap // 1024 // 1024}, PyMuPDF {answer['release']}, "
              f"{os.cpu_count()} processors")
    assert answer["words"] > 0
    assert answer["peak_kib"] * 1024 < 0.75 * cap, answer


# ---------------------------------------------------------------------------
# The check for a running QualCoder, where psutil comes with PyMuPDF 2
# ---------------------------------------------------------------------------

def _psutil_installed():
    try:
        import psutil  # noqa: F401
        return True
    except ImportError:
        return False


def _pythons_unread():
    """Processes named like a Python that give no command line."""
    import psutil
    found = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "status"]):
        name = database._program_name(str(proc.info.get("name") or ""))
        if database._is_a_python(name) and not proc.info.get("cmdline"):
            found.append((proc.info["pid"], name, proc.info.get("status")))
    return found


@pytest.mark.real_process_scan
@pytest.mark.skipif(not _psutil_installed(), reason="psutil not installed")
def test_the_scan_goes_through_psutil_and_reads_command_lines(
        monkeypatch, tmp_path, capsys):
    script = tmp_path / "qualcoder" / "__main__.py"
    script.parent.mkdir()
    script.write_text("import time\ntime.sleep(120)\n", encoding="utf-8")
    calls = []
    real = database._psutil_scan

    def spy(psutil, own_pid):
        calls.append(own_pid)
        return real(psutil, own_pid)
    monkeypatch.setattr(database, "_psutil_scan", spy)
    child = subprocess.Popen([sys.executable, str(script)],
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    import psutil
    try:
        time.sleep(1)
        # the child's command line as the system gives it (a Mac's
        # framework Python starts its app's program in its place)
        cmdline = psutil.Process(child.pid).cmdline()
        database._process_scan_cache["at"] = None
        scan = database._qualcoder_process_scan()
    finally:
        child.kill()
        child.wait()
    assert calls, "the scan did not go through psutil"
    assert scan is not None
    assert cmdline[-1] == str(script), cmdline
    # the child, as the scan keeps a hit (200 characters)
    assert " ".join(cmdline).strip()[:200] in scan.hits, scan
    sandboxed = database._sees_only_its_own_processes()
    if sys.platform in ("win32", "linux") and not sandboxed:
        assert scan.saw_command_lines, _pythons_unread()

    # With the child ended, a fresh chat history: its sign is left out
    # exactly when the scan, which could read command lines, found none
    project = tmp_path / "project.qda"
    (project / "ai_data").mkdir(parents=True)
    (project / "ai_data" / "chat_history.sqlite").write_bytes(b"")
    database._process_scan_cache["at"] = None
    signals = database.qualcoder_gui_signals(project)
    after = database._process_scan_cache["scan"]
    chat = any("chat history" in signal for signal in signals)
    assert after is not None
    assert chat == (not after.found_none), (signals, after)
    with capsys.disabled():
        print(f"\nprocess check, {sys.platform}: through psutil, command "
              f"lines read {after.saw_command_lines}, none found "
              f"{after.found_none}, chat sign given {chat}")


# ---------------------------------------------------------------------------
# NOTICE, and the advisory check
# ---------------------------------------------------------------------------

# Each library PyMuPDF 2 brings, as NOTICE names it with its licence, the
# licence as the files and metadata inside the locked packages give it
NOTICE_ENTRIES = {
    "onnxruntime": "- onnxruntime: MIT, Microsoft Corporation",
    "numpy": "- numpy: BSD-3-Clause, NumPy Developers",
    "networkx": "- networkx: BSD-3-Clause, NetworkX Developers.",
    "psutil": "- psutil: BSD-3-Clause, Jay Loden, Dave Daeschler and "
              "Giampaolo Rodola.",
    "protobuf": "- protobuf: BSD-3-Clause, Google Inc.",
    "pyyaml": "- PyYAML: MIT, Ingy döt Net and Kirill Simonov.",
    "tabulate": "- tabulate: MIT, Sergey Astanin and contributors.",
    "flatbuffers": "- flatbuffers: Apache-2.0, as its metadata says",
    "packaging": "- packaging: Apache-2.0 or BSD-2-Clause, Donald Stufft "
                 "and individual contributors.",
    "pymupdf-layout": "pymupdf-layout and pymupdf4llm, are empty",
    "pymupdf4llm": "pymupdf-layout and pymupdf4llm, are empty",
}


def _what_pymupdf_2_brings():
    """The packages the walk with the part alone (no development tools)
    reaches at 3.13 on a computer on PyMuPDF 2 and on none with 1.x."""
    lock = _lock()
    two, one = set(), set()
    for system, machine in ENVIRONMENTS:
        reached = set(lock_walk_releases(lock, ROOT, system, machine,
                                         root_extras=("pdf-epub",),
                                         python="3.13"))
        (two if (system, machine) in TWO_X else one).update(reached)
    return two - one


def test_notice_names_each_library_pymupdf_2_brings():
    assert _what_pymupdf_2_brings() == set(NOTICE_ENTRIES)
    notice = " ".join((REPO / "NOTICE").read_text(encoding="utf-8")
                      .split())
    for name, words in NOTICE_ENTRIES.items():
        assert words in notice, name
    assert ("under PyMuPDF's statement, \"Dual Licensed - GNU AFFERO GPL "
            "3.0 or Artifex Commercial License\"") in notice
    assert (REPO / "NOTICE").read_bytes() == \
        (REPO / "packaging/pypi-old-name/NOTICE").read_bytes()


def test_notice_names_what_numpys_packages_bundle_where_they_do():
    """As the locked numpy 2.4.6 and 2.5.4 packages hold them: Microsoft's
    C++ runtime (numpy.libs/msvcp140-....dll) in every Windows package,
    though their LICENSE.txt does not name it; libquadmath in the Linux
    x86-64 packages alone (the Arm packages' LICENSE.txt names it, but
    they hold no such file)."""
    notice = " ".join((REPO / "NOTICE").read_text(encoding="utf-8")
                      .split())
    start = notice.index("- numpy:")
    entry = notice[start:notice.index("- networkx:", start)]
    assert "its packages for Windows also contain Microsoft's C++ runtime " \
        "library (msvcp140.dll)" in entry
    assert "on Linux x86-64 libquadmath (LGPL-2.1-or-later)" in entry
    assert "on Linux libquadmath" not in entry


def test_the_advisory_check_asks_about_both_releases():
    pairs = check_advisories.locked_releases(REPO / "uv.lock")
    assert sorted(v for n, v in pairs if n == "pymupdf") == [FIRST, SECOND]
    assert len([v for n, v in pairs if n == "numpy"]) == 2


def test_the_parity_gate_pins_ebooklib_alone():
    """The gate reads PDFs with the PyMuPDF the lock gives Ubuntu on
    Python 3.13 (2.0), so it compares QualCoder's own functions with
    Exegete's under it; it pins the record's EbookLib alone."""
    from test_v012_workflow_pins import WORKFLOWS, _jobs
    job = next(job for job in _jobs(WORKFLOWS / "ci.yml")
               if job["name"] == "qualcoder-parity")
    commands = [line for line in job["lines"]
                if not line.strip().startswith("#")]
    pins = [line for line in commands if "pins=$(" in line]
    assert len(pins) == 1, pins
    assert "'ebooklib==' + v['ebooklib']" in pins[0]
    assert "pymupdf" not in pins[0]
    assert not any("pymupdf==" in line for line in commands)
