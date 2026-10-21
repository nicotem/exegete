"""What the reading touches of the network (the 2.0 trial).

An audit hook records every socket event Python raises (socket.connect,
which connect_ex raises too, socket.sendto, socket.sendmsg,
socket.getaddrinfo, socket.gethostbyname, socket.bind, socket.__new__)
and every process start (subprocess.Popen, os.system, os.exec,
os.posix_spawn), first in a fresh process doing `import pymupdf` alone,
then in the reading process's own child reading each PDF fixture.
Compiled code that calls the system directly is not seen here: on Linux
the job runs this under strace too. Prints JSON: the events, and each
fixture's verdict with a digest of its text, to compare with a run
under `unshare -n`.

  network_probe.py DIR OUT     DIR holds the saved fixtures
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

from exegete import import_reading  # noqa: E402

PACKAGE = str(Path(import_reading.__file__).resolve().parent.parent)

PREFIXES = ("socket.", "subprocess.Popen", "os.system", "os.exec",
            "os.posix_spawn", "os.spawn", "urllib.Request",
            "http.client.connect")
HOOK = (
    "import sys\n"
    "def _hook(event, args, _out=sys.argv[-1]):\n"
    "    if event.startswith(%r):\n"
    "        with open(_out, 'a') as f:\n"
    "            f.write(event + ' ' + repr(args)[:200] + '\\n')\n"
    "sys.addaudithook(_hook)\n" % (PREFIXES,))


def events(path):
    return Path(path).read_text().splitlines() if Path(path).exists() else []


def main(folder, out):
    scratch = Path(tempfile.mkdtemp(prefix="exegete-netprobe-"))
    record = scratch / "import.txt"
    subprocess.run([sys.executable, "-I", "-c", HOOK + "import pymupdf\n",
                    str(record)], check=True)
    child_record = scratch / "reading.txt"
    package = PACKAGE
    import_reading.reader_command = lambda: [
        sys.executable, "-I", "-c",
        HOOK + "sys.path.insert(0, sys.argv[1])\n"
        "from exegete.import_reading import child_main\nchild_main()\n",
        package, str(child_record)]
    readings = {}
    for path in sorted(Path(folder).glob("*.pdf")):
        try:
            got = import_reading.read_in_process("pdf", path.read_bytes())
            readings[path.name] = "ready " + hashlib.sha256(
                got["text"].encode("utf-8", "surrogatepass")).hexdigest()[:16]
        except import_reading.ReadFailed as failed:
            readings[path.name] = "refused " + failed.code + (
                " " + failed.cause["kind"] if failed.cause else "")
    result = {"pymupdf": metadata.version("pymupdf"),
              "import_events": events(record),
              "reading_events": events(child_record),
              "readings": readings}
    Path(out).write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
