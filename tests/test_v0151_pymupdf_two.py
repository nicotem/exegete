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
- Where psutil is installed (it comes with PyMuPDF 2), the check for a
  running QualCoder goes through it and reads command lines.
- NOTICE names every library PyMuPDF 2 brings, with its licence; the
  advisory check asks OSV about each locked release.
"""

import json
import os
import subprocess
import sys
import time
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
# Where the second line, PyMuPDF 2, applies: these, Python 3.11 to 3.14
TWO_X = {("win32", "AMD64"), ("linux", "x86_64"), ("linux", "aarch64")}
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

    @pytest.mark.parametrize("python", ["3.10", "3.11", "3.12", "3.13",
                                        "3.14"])
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
        assert {k for k, v in found.items() if v == SECOND} == TWO_X
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
    try:
        time.sleep(1)
        database._process_scan_cache["at"] = None
        scan = database._qualcoder_process_scan()
    finally:
        child.kill()
        child.wait()
    assert calls, "the scan did not go through psutil"
    assert scan is not None
    # the child's command line, as the scan keeps a hit (200 characters)
    assert " ".join([sys.executable, str(script)])[:200] in scan.hits, scan
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
