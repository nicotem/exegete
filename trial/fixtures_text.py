"""The PDF fixtures' text under each PyMuPDF release (the 2.0 trial).

  write DIR        the five PDF fixtures, made once with this
                   environment's PyMuPDF (1.28.2 from the lock), as files
  read DIR OUT     each saved file read through
                   doc_readers.read_document("pdf", raw), into OUT (JSON)
  compare A B      two readings compared, character by character

The fixtures are Exegete's own test documents; no researcher's text.
Run from the repository root, with the environment's own Python.
"""
import difflib
import json
import sys
from pathlib import Path


def write(folder):
    sys.path.insert(0, "tests")
    import import_fixtures
    folder.mkdir(parents=True, exist_ok=True)
    for name, make in import_fixtures.PDF.items():
        (folder / name).write_bytes(make())


def read(folder, out):
    from importlib import metadata
    from exegete import doc_readers
    files = {}
    for path in sorted(folder.glob("*.pdf")):
        try:
            got = doc_readers.read_document("pdf", path.read_bytes())
            files[path.name] = {"text": got["text"], "notes": got["notes"],
                                "signs": got["signs"]}
        except doc_readers.ReadRefused as refused:
            context = refused.__context__
            files[path.name] = {"refused": refused.code, "behind": (
                type(context).__module__ + "." + type(context).__qualname__
                if context is not None else None)}
    out.write_text(json.dumps({"pymupdf": metadata.version("pymupdf"),
                               "files": files}, ensure_ascii=True, indent=1))


def compare(first, second):
    a, b = (json.loads(p.read_text()) for p in (first, second))
    print(f"PyMuPDF {a['pymupdf']} against {b['pymupdf']}")
    for name in sorted(set(a["files"]) | set(b["files"])):
        x, y = a["files"].get(name, {}), b["files"].get(name, {})
        if x == y:
            print(f"  {name}: the same")
            continue
        print(f"  {name}: differs")
        for key in sorted(set(x) | set(y)):
            p, q = x.get(key), y.get(key)
            if p == q:
                continue
            if isinstance(p, str) and isinstance(q, str):
                ops = difflib.SequenceMatcher(None, p, q, autojunk=False)
                for tag, i1, i2, j1, j2 in ops.get_opcodes():
                    if tag != "equal":
                        print(f"    {key} {tag} at {i1}: {p[i1:i2]!r} -> "
                              f"{q[j1:j2]!r}")
            else:
                print(f"    {key}: {p!r} -> {q!r}")


if __name__ == "__main__":
    command, *rest = sys.argv[1:]
    if command == "write":
        write(Path(rest[0]))
    elif command == "read":
        read(Path(rest[0]), Path(rest[1]))
    else:
        compare(Path(rest[0]), Path(rest[1]))
