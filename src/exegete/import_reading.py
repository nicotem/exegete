# SPDX-License-Identifier: LGPL-3.0-or-later
"""The reading process: each document is read in a separate, short-lived
Python process, so that a hostile or broken file cannot reach the server
itself (0.14.3; the design's Part 5). The server reads no
document itself: plain text and web pages are read as UTF-8, or plain
text in the character set the researcher chose from the preview's
readings (v0.15.1), so the names check searches the text this process
returns, as stored.

The contract, and why each part matters:

- Started with `subprocess`, as the same Python in isolated mode (-I),
  so neither the working folder nor Python's own settings shape it; its
  working folder a private temporary one; a small environment, not the
  host's. Never forked from the server, which holds the open database.
- Given bytes, not paths: the server, which has already opened, checked
  and hashed the file, hands its bytes over standard input, so what was
  hashed is what is read, and the process opens none of the
  researcher's paths.
- Answering in plain data: one JSON document of bounded size on its own
  standard output, which is a private pipe to the server (never the
  server's own channel to the host), checked before use; never Python's
  pickled objects. A refusal carries no text, but for one: a plain text
  file not saved as UTF-8 (`not_utf8`) carries its readings, lines of
  the file as each character set reads them (v0.15.1), checked as
  strictly and dropped, the refusal standing, when they are not as
  Exegete writes them. Its error output is dropped; a library that
  writes to standard output inside the process writes nowhere. A
  `damaged` refusal may carry `cause`, {"kind", "library", "version"}:
  the class of the exception behind it, by module and qualified name
  (`builtins.` left out), the library Exegete reads that kind of file
  with (READER_LIBRARIES, null for none) and the release of it this
  process loaded, so that Exegete's log can say what kind of error lay
  behind the verdict (v0.15.1).
- Usage reports off: PyMuPDF 2.0 loads onnxruntime, whose reports to
  Microsoft are on by default. The small environment carries the setting
  that stops them on Linux and macOS, and before a PDF is read the
  process calls onnxruntime's own switch, the one Windows' reports heed,
  which stops all but the one onnxruntime writes as it loads (v0.15.1).
- Limits: a time limit, and a memory cap on every system (Linux: an
  address-space limit the process sets on itself before it reads
  anything; macOS, which honours no such limit: the server watches the
  process's resident memory and ends it past the cap, and refuses the
  reading when the peak the system recorded for the process, read as it
  ends, passed the cap, so that a burst between two looks is refused
  too; Windows: a job object with a memory limit).

No exception text, library message or process output is ever passed on:
a refusal is one of Exegete's own codes (with, for `not_utf8`, the
readings above, made by Exegete's own code from the file's bytes), and a
cause names a class and a release, never the exception's message,
arguments, traceback or str().
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# One file's reading at the preview (provisional, 0.14.3): within the
# preview's own time (doc_import's CALL_SECONDS_LEAST, the least a call is
# given), so that no call runs past what a host may allow; the import
# gives a file a margin over it.
READ_TIMEOUT_SECONDS = 30.0
MEMORY_CAP_BYTES = 1024 * 1024 * 1024
# A PDF's reading is given more (v0.15.1): PyMuPDF 2.0, which Windows x64
# and Linux read PDFs with from Python 3.11, loads onnxruntime and numpy,
# whose address space reached 1,242 MiB on Linux in the trial of 21
# October 2026, where 1 GiB stopped it; 2 GiB keeps a PDF's own content
# about the room 1.x has under 1 GiB. One figure for PDFs on every
# system, whichever release reads them; every other kind keeps 1 GiB.
PDF_MEMORY_CAP_BYTES = 2 * 1024 * 1024 * 1024
MAX_ANSWER_BYTES = 16 * 1024 * 1024
WATCH_INTERVAL_SECONDS = 0.05
# The library Exegete reads each kind of file with (doc_readers), named
# beside a "damaged" refusal's cause. OpenDocument is read with Python's
# own zipfile and text handling, and defusedxml serves Word alone, so
# every other kind has none.
READER_LIBRARIES = {"pdf": "pymupdf", "epub": "ebooklib",
                    "rtf": "striprtf", "word": "defusedxml"}
# A cause's kind is a dotted name (a class's module and qualified name)
# and its version a release's spelling; anything else drops the cause.
_CAUSE_KIND = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,7}")
_CAUSE_KIND_MAX = 100
_CAUSE_VERSION = re.compile(r"[0-9A-Za-z.+!_-]{1,40}")

_CHILD_CODE = ("import sys; sys.path.insert(0, sys.argv[1]); "
               "from exegete.import_reading import child_main; child_main()")


class ReadFailed(Exception):
    """A file the reading process did not read: Exegete's own reason code
    and any numbers the words need."""

    def __init__(self, code: str, numbers: Optional[Dict[str, Any]] = None,
                 cause: Optional[Dict[str, Any]] = None,
                 readings: Optional[Dict[str, Any]] = None):
        super().__init__(code)
        self.code = code
        self.numbers = numbers or {}
        # What lay behind a "damaged" verdict, for Exegete's log alone:
        # never in args or str(), so no answer carries it.
        self.cause = cause
        # A plain text file not saved as UTF-8: its readings, checked
        # (checked_readings); never in `numbers`.
        self.readings = readings


# ---------------------------------------------------------------------------
# The child
# ---------------------------------------------------------------------------

def _limit_own_memory(cap: int) -> None:
    if not sys.platform.startswith("linux"):
        return
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    except (ImportError, ValueError, OSError):
        pass


def child_main() -> None:
    """The reading process's whole life: one header line and the bytes
    in, one JSON answer out."""
    import warnings
    warnings.simplefilter("ignore")
    answer_fd = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    sys.stdout = open(os.devnull, "w")
    sys.stderr = sys.stdout
    try:
        header = json.loads(sys.stdin.buffer.readline(4096).decode("ascii"))
        _limit_own_memory(int(header["memory"]))
        size = int(header["size"])
        raw = sys.stdin.buffer.read(size)
        if len(raw) != size:
            answer = {"ok": False, "refusal": "reader_failed"}
        else:
            answer = _read(header, raw)
    except MemoryError:
        answer = {"ok": False, "refusal": "reader_memory"}
    except Exception:
        answer = {"ok": False, "refusal": "reader_failed"}
    try:
        payload = json.dumps(answer, ensure_ascii=True).encode("ascii")
    except Exception:
        payload = b'{"ok": false, "refusal": "reader_failed"}'
    with os.fdopen(answer_fd, "wb") as out:
        out.write(payload)
    os._exit(0)


def _hidden_class(refused: BaseException) -> Optional[type]:
    """The class of the exception a refusal was raised over: the readers
    raise it `from None` inside an `except`, which hides that exception
    but keeps it as the context; None when it has none."""
    context = refused.__context__
    return None if context is None else type(context)


def _cause(behind: Optional[type], kind: str) -> Optional[Dict[str, Any]]:
    """What lay behind a "damaged" verdict, from the class of the exception
    behind it alone (`behind`; None, nothing to name: no cause): its
    module and qualified name, the library Exegete reads `kind` with and
    the release of it this process loaded. Never the exception itself,
    so never its message, arguments or traceback. On any failure here,
    no cause, so a verdict never changes; a release not found leaves the
    kind."""
    if behind is None:
        return None
    try:
        module, name = behind.__module__, behind.__qualname__
        label = name if module == "builtins" else f"{module}.{name}"
        library = READER_LIBRARIES.get(kind)
    except Exception:
        return None
    version = None
    if library is not None:
        try:
            from importlib import metadata
            version = metadata.version(library)
        except Exception:
            version = None
    return {"kind": label, "library": library, "version": version}


def _damaged(behind: Optional[type], kind: str,
             answer: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    answer = answer or {"ok": False, "refusal": "damaged"}
    cause = _cause(behind, kind)
    if cause is not None:
        answer["cause"] = cause
    return answer


def _onnxruntime_reports_off() -> None:
    """Before PyMuPDF loads (v0.15.1). PyMuPDF 2.0 loads onnxruntime as
    it is imported and starts its models, and onnxruntime's usage reports
    to Microsoft are on by default. ORT_DISABLE_TELEMETRY
    (env_settings.READER_SETTINGS) stops them all on Linux and macOS. On
    Windows they go through the system's event tracing, which reads no
    setting: onnxruntime's own switch, called here once it has loaded and
    before PyMuPDF starts its models, stops every report after the one it
    writes as it loads, which nothing in Python can reach (PRIVACY.md
    says so). Where onnxruntime is not installed (PyMuPDF 1.x), nothing
    is loaded; if it cannot load, PyMuPDF reads without it, as before."""
    try:
        import onnxruntime
    except ImportError:
        return
    except Exception:
        return
    try:
        onnxruntime.disable_telemetry_events()
    except Exception:
        pass


def _read(header: Dict[str, Any], raw: bytes) -> Dict[str, Any]:
    from . import doc_readers
    kind = str(header["kind"])
    if kind == "pdf":
        _onnxruntime_reports_off()
    chosen = {}
    if "character_set" in header:
        # The set the researcher chose (v0.15.1), sent only when given.
        chosen["character_set"] = str(header["character_set"])
    try:
        result = doc_readers.read_document(kind, raw, **chosen)
    except doc_readers.ReadRefused as refused:
        answer = {"ok": False, "refusal": refused.code,
                  "numbers": {k: v for k, v in refused.numbers.items()
                              if isinstance(v, int)}}
        if refused.code == "damaged":
            return _damaged(_hidden_class(refused), kind, answer)
        if (refused.code == "not_utf8" and not chosen
                and kind in doc_readers.PLAIN_FORMATS):
            # The readings the preview shows (v0.15.1); any failure here
            # leaves the refusal as it was.
            try:
                answer["readings"] = doc_readers.readings_of(
                    raw, int(header.get("max_characters", 0)))
            except Exception:
                pass
        return answer
    except MemoryError:
        return {"ok": False, "refusal": "reader_memory"}
    except RecursionError as error:
        return _damaged(type(error), kind)
    except Exception as error:
        return _damaged(type(error), kind)
    limit = int(header.get("max_characters", 0))
    if limit and result["characters"] > limit:
        return {"ok": False, "refusal": "too_long",
                "numbers": {"characters": result["characters"],
                            "limit": limit}}
    return {"ok": True, "result": result}


# ---------------------------------------------------------------------------
# Memory caps the server applies from outside
# ---------------------------------------------------------------------------

_LIBPROC: Dict[str, Any] = {}


def _mac_resident_bytes(pid: int) -> Optional[int]:
    """A process's resident memory on macOS, from libproc's
    proc_pidinfo(PROC_PIDTASKINFO), whose answer starts with the virtual
    and the resident size; or None when it cannot be read."""
    import ctypes
    if "lib" not in _LIBPROC:
        try:
            lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int,
                                         ctypes.c_uint64, ctypes.c_void_p,
                                         ctypes.c_int]
            lib.proc_pidinfo.restype = ctypes.c_int
        except (OSError, AttributeError):
            lib = None
        _LIBPROC["lib"] = lib
    lib = _LIBPROC["lib"]
    if lib is None:
        return None
    buffer = (ctypes.c_uint64 * 12)()
    filled = lib.proc_pidinfo(pid, 4, 0, ctypes.byref(buffer),
                              ctypes.sizeof(buffer))
    if filled < 16:
        return None
    return int(buffer[1])


def _mac_ended(process: "subprocess.Popen"
               ) -> Tuple[bool, Optional[int]]:
    """(ended, peak) for a reading process on macOS. The server watches
    the process's memory only every WATCH_INTERVAL_SECONDS, and a burst
    can rise and end between two looks; so the process is collected here
    with wait4 rather than by `poll`, which would discard the system's
    record of its peak resident memory (ru_maxrss, in bytes on macOS, the
    process's own: measured, a parent of 1.5 GB does not raise it). The
    peak is None while the process runs, or when another part of the
    host collected it first (then the looks alone have watched it)."""
    try:
        pid, status, usage = os.wait4(process.pid, os.WNOHANG)
    except ChildProcessError:
        return process.poll() is not None, None
    if pid == 0:
        return False, None
    process.returncode = os.waitstatus_to_exitcode(status)
    return True, int(usage.ru_maxrss)


class _WindowsJob:
    """A job object holding the reading process, with a memory limit per
    process: an allocation past it fails inside the process."""

    def __init__(self, process: "subprocess.Popen", cap: int):
        import ctypes
        from ctypes import wintypes
        self.handle = None
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p,
                                              wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE,
                                                      wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32 = kernel32

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount",
                "OtherOperationCount", "ReadTransferCount",
                "WriteTransferCount", "OtherTransferCount")]

        class BasicLimits(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BasicLimits),
                        ("IoInfo", IoCounters),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            raise OSError("job object")
        self.handle = job
        limits = ExtendedLimits()
        # JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        limits.BasicLimitInformation.LimitFlags = 0x100 | 0x2000
        limits.ProcessMemoryLimit = cap
        if not kernel32.SetInformationJobObject(
                job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise OSError("job object limits")
        if not kernel32.AssignProcessToJobObject(job, int(process._handle)):
            self.close()
            raise OSError("job object assignment")

    def close(self) -> None:
        if self.handle:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None


# ---------------------------------------------------------------------------
# The server's side
# ---------------------------------------------------------------------------

def _package_parent() -> str:
    """The folder holding this `exegete` package, which the reading
    process puts first on its path, so it runs this same code."""
    return str(Path(__file__).resolve().parent.parent)


def _small_environment() -> Dict[str, str]:
    from .env_settings import reader_process_environment
    return reader_process_environment()


def reader_command() -> list:
    return [sys.executable, "-I", "-c", _CHILD_CODE, _package_parent()]


def memory_cap_for(kind: str) -> int:
    """The memory a reading of this kind of file is given: 2 GiB for a
    PDF, 1 GiB for every other kind (v0.15.1)."""
    return PDF_MEMORY_CAP_BYTES if kind == "pdf" else MEMORY_CAP_BYTES


def read_in_process(kind: str, data: bytes, max_characters: int = 0,
                    timeout: float = READ_TIMEOUT_SECONDS,
                    memory_cap: Optional[int] = None,
                    character_set: Optional[str] = None) -> Dict[str, Any]:
    """Read one document's bytes in a reading process and return
    `doc_readers.read_document`'s answer, checked; or raise ReadFailed
    with Exegete's own reason code. `memory_cap`: when not given, the
    kind's own (`memory_cap_for`). `character_set`: the reading the
    researcher chose for a plain text file not saved as UTF-8 (a key of
    `doc_readers.READINGS`), sent only when given."""
    if memory_cap is None:
        memory_cap = memory_cap_for(kind)
    fields = {"kind": kind, "size": len(data), "memory": int(memory_cap),
              "max_characters": int(max_characters)}
    if character_set is not None:
        fields["character_set"] = str(character_set)
    header = json.dumps(fields, ensure_ascii=True).encode("ascii") + b"\n"
    workdir = tempfile.mkdtemp(prefix="exegete-reader-")
    job = None
    try:
        creation = 0
        if os.name == "nt":
            creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            reader_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, cwd=workdir, env=_small_environment(),
            close_fds=True, creationflags=creation)
        if os.name == "nt":
            try:
                job = _WindowsJob(process, memory_cap)
            except Exception:
                process.kill()
                process.wait()
                raise ReadFailed("reader_failed")
        return _talk(process, header + data, timeout, memory_cap, kind)
    finally:
        if job is not None:
            job.close()
        shutil.rmtree(workdir, ignore_errors=True)


def _talk(process: "subprocess.Popen", payload: bytes, timeout: float,
          memory_cap: int, kind: Optional[str] = None) -> Dict[str, Any]:
    received = bytearray()
    overflow = threading.Event()

    def write():
        try:
            process.stdin.write(payload)
        except (OSError, ValueError):
            pass
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    def read():
        while True:
            try:
                chunk = process.stdout.read(65536)
            except (OSError, ValueError):
                return
            if not chunk:
                return
            if len(received) + len(chunk) > MAX_ANSWER_BYTES:
                overflow.set()
                return
            received.extend(chunk)

    writer = threading.Thread(target=write, daemon=True)
    reader = threading.Thread(target=read, daemon=True)
    writer.start()
    reader.start()
    started = time.monotonic()
    reason = None
    peak = None
    while True:
        if sys.platform == "darwin":
            ended, peak = _mac_ended(process)
        else:
            ended = process.poll() is not None
        if ended:
            break
        if time.monotonic() - started > timeout:
            reason = "reader_timeout"
        elif overflow.is_set():
            reason = "reader_failed"
        elif sys.platform == "darwin":
            resident = _mac_resident_bytes(process.pid)
            if resident is not None and resident > memory_cap:
                reason = "reader_memory"
        if reason is not None:
            process.kill()
            break
        time.sleep(WATCH_INTERVAL_SECONDS)
    process.wait()
    reader.join(timeout=5)
    writer.join(timeout=5)
    try:
        process.stdout.close()
    except OSError:
        pass
    if reason is None and peak is not None and peak > memory_cap:
        # Over the cap between two looks (macOS): refused whatever it
        # answered, as it would have been had a look fallen in the burst.
        reason = "reader_memory"
    if reason is not None:
        raise ReadFailed(reason)
    if overflow.is_set():
        raise ReadFailed("reader_failed")
    return _checked_answer(bytes(received), kind)


def _checked_answer(raw: bytes, kind: Optional[str] = None
                    ) -> Dict[str, Any]:
    """The child's answer, its shape checked before anything uses it."""
    try:
        answer = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise ReadFailed("reader_failed") from None
    return checked_result(answer, kind)


def _checked_cause(cause: Any, code: str,
                   kind: Optional[str]) -> Optional[Dict[str, Any]]:
    """A refusal's cause, kept only beside `damaged` and only in its own
    shape: exactly its three keys, a dotted name of at most 100
    characters, the library READER_LIBRARIES gives the kind asked for
    (none for no kind), and a release's spelling or null (null whenever
    the library is). None otherwise: the cause is dropped whole and the
    refusal stands as sent."""
    if code != "damaged" or not isinstance(cause, dict) \
            or set(cause) != {"kind", "library", "version"}:
        return None
    label, library, version = (cause["kind"], cause["library"],
                               cause["version"])
    if not isinstance(label, str) or len(label) > _CAUSE_KIND_MAX \
            or _CAUSE_KIND.fullmatch(label) is None:
        return None
    expected = READER_LIBRARIES.get(kind) if isinstance(kind, str) else None
    if library != expected:
        return None
    if version is not None and (
            library is None or not isinstance(version, str)
            or _CAUSE_VERSION.fullmatch(version) is None):
        return None
    return {"kind": label, "library": library, "version": version}


def checked_result(answer: Any, kind: Optional[str] = None
                   ) -> Dict[str, Any]:
    """A parsed answer, its shape checked: the text, signs, notes,
    character set and counts, or ReadFailed with the child's own code (or
    `reader_failed`) and, beside `damaged`, its cause as `_checked_cause`
    keeps it for the file's `kind`. The import checks a kept answer the
    same way (kept_texts), wrapped as the child sends it."""
    if not isinstance(answer, dict) or not isinstance(answer.get("ok"), bool):
        raise ReadFailed("reader_failed")
    if not answer["ok"]:
        code = answer.get("refusal")
        numbers = answer.get("numbers") or {}
        if not isinstance(code, str) or not code.isascii() or len(code) > 40:
            raise ReadFailed("reader_failed")
        if not isinstance(numbers, dict):
            numbers = {}
        readings = None
        if code == "not_utf8" and "readings" in answer:
            readings = checked_readings(answer["readings"])
        raise ReadFailed(code, {k: v for k, v in numbers.items()
                                if isinstance(k, str) and isinstance(v, int)},
                         cause=_checked_cause(answer.get("cause"), code, kind),
                         readings=readings)
    result = answer.get("result")
    if not isinstance(result, dict):
        raise ReadFailed("reader_failed")
    text = result.get("text")
    signs = result.get("signs")
    notes = result.get("notes")
    if (not isinstance(text, str) or not isinstance(signs, dict)
            or not isinstance(notes, list)
            or not all(isinstance(k, str) and isinstance(v, int)
                       for k, v in signs.items())
            or not all(isinstance(n, dict)
                       and isinstance(n.get("page"), int)
                       and isinstance(n.get("content"), str)
                       for n in notes)):
        raise ReadFailed("reader_failed")
    charset = result.get("charset")
    if charset is not None and not (isinstance(charset, str)
                                    and charset.isascii()
                                    and len(charset) <= 40):
        raise ReadFailed("reader_failed")
    return {"text": text, "signs": dict(signs),
            "notes": [{"page": n["page"], "content": n["content"]}
                      for n in notes],
            "charset": charset,
            "words": len(text.split()), "characters": len(text)}


def checked_readings(readings: Any) -> Optional[Dict[str, Any]]:
    """A `not_utf8` refusal's readings (v0.15.1), their shape checked:
    `{"too_long": true}` alone, or at most one choice for each of
    `doc_readers.READINGS`, each under a key of its own with its names
    from the table and the same number of windows, at most READING_KEPT,
    each a string of at most READING_WINDOW characters, and the sets not
    offered, each a known key. Anything else: None, and the refusal
    stands without them. Nothing about them is logged."""
    from . import doc_readers
    names = doc_readers.READING_NAMES
    if not isinstance(readings, dict):
        return None
    if set(readings) == {"too_long"}:
        return {"too_long": True} if readings["too_long"] is True else None
    if set(readings) != {"choices", "not_offered"}:
        return None
    choices, not_offered = readings["choices"], readings["not_offered"]
    if (not isinstance(choices, list) or not isinstance(not_offered, list)
            or len(choices) > len(names)
            or not all(isinstance(k, str) and k in names
                       for k in not_offered)):
        return None
    seen, counts, out = set(), set(), []
    for choice in choices:
        if not isinstance(choice, dict) or set(choice) != {
                "key", "names", "windows"}:
            return None
        key, said, windows = (choice["key"], choice["names"],
                              choice["windows"])
        if (not isinstance(key, str) or key not in names or key in seen
                or not isinstance(said, list) or not said
                or said[0] != names[key]
                or not all(isinstance(n, str) and n in names.values()
                           for n in said)
                or not isinstance(windows, list)
                or len(windows) > doc_readers.READING_KEPT
                or not all(isinstance(w, str)
                           and len(w) <= doc_readers.READING_WINDOW
                           for w in windows)):
            return None
        seen.add(key)
        counts.add(len(windows))
        out.append({"key": key, "names": list(said),
                    "windows": list(windows)})
    if len(counts) > 1:
        return None
    return {"choices": out, "not_offered": list(not_offered)}
