# SPDX-License-Identifier: LGPL-3.0-or-later
"""The reading process: each document is read in a separate, short-lived
Python process, so that a hostile or broken file cannot reach the server
itself (0.14.3, provisional; the design's Part 5).

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
  pickled objects. Its error output is dropped; a library that writes to
  standard output inside the process writes nowhere.
- Limits: a time limit, and a memory cap on every system (Linux: an
  address-space limit the process sets on itself before it reads
  anything; macOS: the server watches the process's resident memory and
  ends it past the cap; Windows: a job object with a memory limit).

No exception text, library message or process output is ever passed on:
a refusal is one of Exegete's own codes.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

READ_TIMEOUT_SECONDS = 60.0
MEMORY_CAP_BYTES = 1024 * 1024 * 1024
MAX_ANSWER_BYTES = 16 * 1024 * 1024
WATCH_INTERVAL_SECONDS = 0.05

_CHILD_CODE = ("import sys; sys.path.insert(0, sys.argv[1]); "
               "from exegete.import_reading import child_main; child_main()")


class ReadFailed(Exception):
    """A file the reading process did not read: Exegete's own reason code
    and any numbers the words need."""

    def __init__(self, code: str, numbers: Optional[Dict[str, Any]] = None):
        super().__init__(code)
        self.code = code
        self.numbers = numbers or {}


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


def _read(header: Dict[str, Any], raw: bytes) -> Dict[str, Any]:
    from . import doc_readers
    try:
        result = doc_readers.read_document(
            str(header["kind"]), raw, header.get("encoding"))
    except doc_readers.ReadRefused as refused:
        return {"ok": False, "refusal": refused.code,
                "numbers": {k: v for k, v in refused.numbers.items()
                            if isinstance(v, int)}}
    except MemoryError:
        return {"ok": False, "refusal": "reader_memory"}
    except RecursionError:
        return {"ok": False, "refusal": "damaged"}
    except Exception:
        return {"ok": False, "refusal": "damaged"}
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


def read_in_process(kind: str, data: bytes, encoding: Optional[str] = None,
                    max_characters: int = 0,
                    timeout: float = READ_TIMEOUT_SECONDS,
                    memory_cap: int = MEMORY_CAP_BYTES) -> Dict[str, Any]:
    """Read one document's bytes in a reading process and return
    `doc_readers.read_document`'s answer, checked; or raise ReadFailed
    with Exegete's own reason code."""
    header = json.dumps({"kind": kind, "encoding": encoding,
                         "size": len(data), "memory": int(memory_cap),
                         "max_characters": int(max_characters)},
                        ensure_ascii=True).encode("ascii") + b"\n"
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
        return _talk(process, header + data, timeout, memory_cap)
    finally:
        if job is not None:
            job.close()
        shutil.rmtree(workdir, ignore_errors=True)


def _talk(process: "subprocess.Popen", payload: bytes, timeout: float,
          memory_cap: int) -> Dict[str, Any]:
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
    while process.poll() is None:
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
    if reason is not None:
        raise ReadFailed(reason)
    if overflow.is_set():
        raise ReadFailed("reader_failed")
    return _checked_answer(bytes(received))


def _checked_answer(raw: bytes) -> Dict[str, Any]:
    """The child's answer, its shape checked before anything uses it."""
    try:
        answer = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise ReadFailed("reader_failed") from None
    if not isinstance(answer, dict) or not isinstance(answer.get("ok"), bool):
        raise ReadFailed("reader_failed")
    if not answer["ok"]:
        code = answer.get("refusal")
        numbers = answer.get("numbers") or {}
        if not isinstance(code, str) or not code.isascii() or len(code) > 40:
            raise ReadFailed("reader_failed")
        if not isinstance(numbers, dict):
            numbers = {}
        raise ReadFailed(code, {k: v for k, v in numbers.items()
                                if isinstance(k, str) and isinstance(v, int)})
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
            "charset_guessed": bool(result.get("charset_guessed")),
            "words": len(text.split()), "characters": len(text)}
