"""The memory a PDF reading needs, under each PyMuPDF release (Linux).

At each cap (1, 1.5, 2, 3 and 4 GiB), RUNS times: Exegete's own verdict,
read_in_process("pdf", three_pages.pdf, memory_cap=cap); and a probe
child that sets the same address-space limit (RLIMIT_AS, as the reading
process does on Linux), imports pymupdf, reads the same bytes through
doc_readers.read_document and prints the class of any failure, VmPeak
and VmHWM from /proc/self/status. VmPeak is the address space the cap
limits; VmHWM is resident memory, closer to what Windows' job object
counts (committed memory, not measured here).

  memory_probe.py DIR RUNS OUT
"""
import json
import subprocess
import sys
from collections import Counter
from importlib import metadata
from pathlib import Path

from exegete import import_reading  # noqa: E402

PACKAGE = str(Path(import_reading.__file__).resolve().parent.parent)

GIB = 1024 ** 3
CAPS = (1, 1.5, 2, 3, 4)
PROBE = r"""
import json, resource, sys
cap = int(sys.argv[1]); sys.path.insert(0, sys.argv[2])
resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
raw = sys.stdin.buffer.read()
failure = None
try:
    import pymupdf
    from exegete import doc_readers
    doc_readers.read_document("pdf", raw)
except BaseException as error:
    failure = type(error).__module__ + "." + type(error).__qualname__
    if error.__context__ is not None:
        c = type(error.__context__)
        failure += " behind " + c.__module__ + "." + c.__qualname__
status = {}
for line in open("/proc/self/status"):
    key, _, value = line.partition(":")
    if key in ("VmPeak", "VmHWM"):
        status[key] = int(value.split()[0]) // 1024
print(json.dumps({"failure": failure, **status}))
"""


def main(folder, runs, out):
    raw = (Path(folder) / "three_pages.pdf").read_bytes()
    table = []
    for cap in CAPS:
        limit = int(cap * GIB)
        verdicts, failures, peaks, resident = Counter(), Counter(), [], []
        for _ in range(runs):
            try:
                import_reading.read_in_process("pdf", raw, memory_cap=limit)
                verdicts["ready"] += 1
            except import_reading.ReadFailed as failed:
                verdicts[failed.code + (" " + failed.cause["kind"]
                                        if failed.cause else "")] += 1
            probe = subprocess.run(
                [sys.executable, "-I", "-c", PROBE, str(limit),
                 PACKAGE], input=raw, capture_output=True)
            try:
                seen = json.loads(probe.stdout.decode().strip().splitlines()[-1])
            except Exception:
                seen = {"failure": f"probe ended {probe.returncode}"}
            failures[seen.get("failure") or "none"] += 1
            if "VmPeak" in seen:
                peaks.append(seen["VmPeak"])
                resident.append(seen["VmHWM"])
        row = {"cap_gib": cap, "verdicts": dict(verdicts),
               "probe_failures": dict(failures),
               "vmpeak_mib": [min(peaks), max(peaks)] if peaks else None,
               "vmhwm_mib": [min(resident), max(resident)] if resident else None}
        table.append(row)
        print(json.dumps(row), flush=True)
    Path(out).write_text(json.dumps({"pymupdf": metadata.version("pymupdf"),
                                     "runs": runs, "caps": table}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
