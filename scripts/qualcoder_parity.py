# SPDX-License-Identifier: LGPL-3.0-or-later
"""Record what QualCoder's own import stores from each test document
(0.14.3; design Part 10).

Given a QualCoder source tree, this runs QualCoder's own extraction
functions, cut out of its files without its interface (no PyQt), on every
document `tests/import_fixtures.py` builds, and writes what QualCoder
would store from each: its text, or that it refuses the file, fails on
it, or stores noise (the raw file, when it finds no text). The tests
compare Exegete's text with these, character for character.

Nothing is retyped: each function's source is taken from QualCoder's
file with `ast` and run in a namespace holding only the libraries it
needs. The order of the steps around them follows `load_file_text`
(`manage_files.py` 3213-3341 at 9bddf17, 3248-3376 in the 4.0 release)
and, for subtitle files, `import_transcription_from_file` (2484-2505 at
9bddf17). QualCoder itself, with its interface, is never run. The record
in the tests is the 4.0 release's (tag 4.0, commit b95e021):

    python scripts/qualcoder_parity.py --qualcoder <tree> --commit <sha> --out <json>
    python scripts/qualcoder_parity.py --qualcoder <tree> --check <json>

`--check` compares a fresh run with a recorded one and lists any file
whose outcome changed (the CI watch on QualCoder's newest code).
"""

import argparse
import ast
import builtins
import gc
import json
import logging
import platform
import re
import shutil
import sqlite3
import sys
import tempfile
import textwrap
import types
import zipfile
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))

import import_fixtures  # noqa: E402

builtins._ = getattr(builtins, "_", lambda s: s)   # QualCoder's gettext


def _source_dir(tree: Path) -> Path:
    for candidate in (tree / "src" / "qualcoder", tree):
        if (candidate / "manage_files.py").is_file():
            return candidate
    raise SystemExit(f"no QualCoder source under {tree}")


def _segments(path: Path, names, cls=None):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    nodes = tree.body
    if cls is not None:
        nodes = next(n for n in tree.body
                     if isinstance(n, ast.ClassDef) and n.name == cls).body
    found = {}
    for node in nodes:
        name = None
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            name = node.name
        elif isinstance(node, ast.Assign) and isinstance(
                node.targets[0], ast.Name):
            name = node.targets[0].id
        if name in names:
            found[name] = textwrap.dedent(ast.get_source_segment(src, node))
    missing = set(names) - set(found)
    if missing:
        raise SystemExit(f"{path.name}: not found: {sorted(missing)}")
    return [found[n] for n in names]


def _load(path: Path, names, ns, cls=None):
    for segment in _segments(path, names, cls):
        exec(compile(segment, str(path), "exec"), ns)
    return ns


def _ns():
    return {"logging": logging, "logger": logging.getLogger("qc"),
            "re": re, "zipfile": zipfile, "Path": Path,
            "__name__": "qualcoder_parity"}


class QualCoder:
    """QualCoder's extraction functions from one source tree."""

    def __init__(self, tree: Path, optional: bool):
        src = _source_dir(tree)
        html_src = (src / "html_parser.py").read_text(encoding="utf-8")
        html_ns = _ns()
        exec(compile(html_src, "html_parser.py", "exec"), html_ns)
        self.html_to_text = html_ns["html_to_text"]
        import xml.etree.ElementTree as etree
        ns = _ns()
        ns["etree"] = etree
        self.docx = _load(src / "docx.py",
                          ["nsprefixes", "opendocx", "getdocumenttext"], ns)
        from charset_normalizer import from_bytes
        ns = _ns()
        ns["from_bytes"] = from_bytes
        _load(src / "text_decoding.py", ["decode_text_with_best_encoding"],
              ns)
        self.decode = ns["decode_text_with_best_encoding"]
        ns = _ns()
        _load(src / "manage_files.py", ["convert_odt_to_text"], ns,
              cls="DialogManageFiles")
        self.odt = ns["convert_odt_to_text"]
        self.epub = self.pdf = None
        if optional:
            package = types.ModuleType("qualcoder")
            package.__path__ = []
            parser = types.ModuleType("qualcoder.html_parser")
            parser.html_to_text = self.html_to_text
            sys.modules.setdefault("qualcoder", package)
            sys.modules["qualcoder.html_parser"] = parser
            ns = _ns()
            ns.update(__package__="qualcoder", __name__="qualcoder.helpers")
            _load(src / "helpers.py", ["extract_epub_fulltext"], ns)
            self.epub = ns["extract_epub_fulltext"]
            import pymupdf
            ns = _ns()
            ns["pymupdf"] = pymupdf
            self.pdf = _load(src / "pdf_utils.py", [
                "_word_flags", "_page_words_raw", "_build_page_text",
                "_extract_page", "extract_pdf_fulltext",
                "extract_pdf_annotations", "extract_pdf_highlights"], ns)

    # -- load_file_text, less its interface (3213-3341) ---------------------

    def stored(self, path: Path) -> dict:
        """What QualCoder's import would store from `path`."""
        suffix = path.suffix.lower()
        if suffix in (".srt", ".vtt"):
            return self._transcript(path)
        if suffix not in (".docx", ".odt", ".rtf", ".txt", ".htm", ".html",
                          ".epub", ".md", ".pdf"):
            return {"refused": "not a supported type"}
        text_ = ""
        try:
            if suffix == ".odt":
                text_ = self.odt(None, str(path)).replace("\n", "\n\n")
            if suffix == ".docx":
                text_ = "\n\n".join(self.docx["getdocumenttext"](
                    self.docx["opendocx"](str(path))))
            if suffix == ".rtf":
                from striprtf.striprtf import rtf_to_text
                with open(path, "r", encoding="latin-1") as handle:
                    try:
                        text_ = rtf_to_text(handle.read())
                    except Exception:
                        text_ = ""
            if suffix == ".epub":
                text_ = self.epub(str(path))
            if suffix in (".html", ".htm"):
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    html_text = ""
                    while 1:
                        line = handle.readline()
                        if not line:
                            break
                        html_text += line
                text_ = self.html_to_text(html_text)
            if suffix == ".pdf":
                try:
                    text_ = self.pdf["extract_pdf_fulltext"](
                        str(path), None, join_lines=True)
                except ValueError:
                    return {"refused": "password protected"}
                except Exception:
                    return {"refused": "damaged or unreadable"}
        except Exception as err:
            return {"error": type(err).__name__}
        fallback = False
        if text_ == "" and suffix not in (".pdf", ".tex"):
            text_, _encoding = self.decode(path)
            fallback = suffix not in (".txt", ".md")
            if text_ and text_[0] == "\ufeff":
                text_ = text_[1:]
        if text_ == "":
            return {"refused": "empty"}
        if suffix != ".pdf":
            text_ = text_.replace("\r\n", "\n").replace("\r", "\n")
            if text_ and text_[0] == "\ufeff":
                text_ = text_[1:]
        problem = _storable(text_)
        if problem:
            return {"error": problem}
        out = {"text": text_}
        if fallback:
            out["noise"] = True
        if suffix == ".pdf":
            notes = self.pdf["extract_pdf_annotations"](str(path))
            if notes:
                out["memo"] = "\n".join(
                    ["PDF annotations:"]
                    + [f"[p. {n['page']}] {n['content']}" for n in notes])
            out["markups"] = len(self.pdf["extract_pdf_highlights"](
                str(path)))
        return out

    def _transcript(self, path: Path) -> dict:
        """`import_transcription_from_file` (2484-2505), for subtitles."""
        text_, _encoding = self.decode(path)
        text_ = text_.replace("\r\n", "\n").replace("\r", "\n")
        if text_ and text_[0] == "\ufeff":
            text_ = text_[1:]
        if text_.strip() == "":
            return {"refused": "no readable text"}
        return {"text": text_}


def _storable(text: str) -> str:
    """Whether SQLite can store the text, as QualCoder's insert would."""
    con = sqlite3.connect(":memory:")
    try:
        con.execute("create table source (fulltext text)")
        con.execute("insert into source values (?)", (text,))
        return ""
    except Exception as err:
        return type(err).__name__
    finally:
        con.close()


def _versions() -> dict:
    out = {"python": platform.python_version()}
    for name in ("charset-normalizer", "striprtf", "pymupdf", "ebooklib",
                 "lxml"):
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def run(tree: Path) -> dict:
    optional = import_fixtures.optional_part_installed()
    qualcoder = QualCoder(tree, optional)
    files = {}
    folder = tempfile.mkdtemp(prefix="qualcoder-parity-")
    for name, path in sorted(import_fixtures.write_all(
            Path(folder), optional).items()):
        files[name] = qualcoder.stored(path)
    # PyMuPDF may hold a document's file until it is collected; Windows
    # will not remove a file still open.
    gc.collect()
    shutil.rmtree(folder, ignore_errors=True)
    return {"qualcoder_source": str(tree), "versions": _versions(),
            "files": files}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--qualcoder", required=True, type=Path)
    parser.add_argument("--commit", default="",
                        help="the QualCoder commit the tree is at")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    result = run(args.qualcoder)
    result["qualcoder_commit"] = args.commit
    if args.out:
        result.pop("qualcoder_source")
        args.out.write_text(json.dumps(result, indent=1, ensure_ascii=True,
                                       sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"wrote {len(result['files'])} outcomes to {args.out}")
    if args.check:
        recorded = json.loads(args.check.read_text(encoding="utf-8"))
        changed = sorted(name for name, outcome in result["files"].items()
                         if recorded["files"].get(name) != outcome)
        for name in changed:
            print(f"changed: {name}")
        print(f"{len(changed)} of {len(result['files'])} outcomes changed "
              f"since the recorded run")
        return 1 if changed else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
