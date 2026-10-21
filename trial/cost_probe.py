"""What one reading process costs under each PyMuPDF release.

Five fresh processes, each timing `import pymupdf` and the reading of
three_pages.pdf through doc_readers.read_document, and giving its peak
resident memory (Linux VmHWM; macOS ru_maxrss; Windows the peak working
set and the peak committed memory, which the job object limits); then
the size installed of every distribution in the environment, with the
total. Prints JSON.

  cost_probe.py DIR OUT
"""
import json
import statistics
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import exegete  # noqa: E402

PACKAGE = str(Path(exegete.__file__).resolve().parent.parent)
CHILD = r"""
import json, sys, time
t0 = time.perf_counter()
import pymupdf
t1 = time.perf_counter()
sys.path.insert(0, sys.argv[1])
from exegete import doc_readers
raw = sys.stdin.buffer.read()
t2 = time.perf_counter()
doc_readers.read_document("pdf", raw)
t3 = time.perf_counter()
peak = {}
if sys.platform.startswith("linux"):
    for line in open("/proc/self/status"):
        key, _, value = line.partition(":")
        if key == "VmHWM":
            peak["resident_mib"] = int(value.split()[0]) // 1024
elif sys.platform == "darwin":
    import resource
    peak["resident_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 2**20
else:
    import ctypes
    from ctypes import wintypes
    class C(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize",
            "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    c = C(); c.cb = ctypes.sizeof(C)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    peak["resident_mib"] = c.PeakWorkingSetSize // 2**20
    peak["committed_mib"] = c.PeakPagefileUsage // 2**20
print(json.dumps({"import_s": t1 - t0, "read_s": t3 - t2, **peak}))
"""


def main(folder, out):
    raw = (Path(folder) / "three_pages.pdf").read_bytes()
    runs = []
    for _ in range(5):
        done = subprocess.run([sys.executable, "-I", "-c", CHILD,
                               PACKAGE], input=raw,
                              capture_output=True, check=True)
        runs.append(json.loads(done.stdout.decode().strip().splitlines()[-1]))
    summary = {k: [round(min(r[k] for r in runs), 3),
                   round(statistics.median(r[k] for r in runs), 3),
                   round(max(r[k] for r in runs), 3)]
               for k in runs[0]}
    sizes = {}
    for dist in metadata.distributions():
        total = 0
        for f in dist.files or []:
            try:
                total += f.locate().stat().st_size
            except OSError:
                pass
        sizes[f"{dist.metadata['Name']} {dist.version}"] = total // 1024
    result = {"pymupdf": metadata.version("pymupdf"),
              "first_run": runs[0], "min_median_max": summary,
              "installed_kib_total": sum(sizes.values()),
              "installed_kib": dict(sorted(sizes.items()))}
    Path(out).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items()
                      if k != "installed_kib"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
