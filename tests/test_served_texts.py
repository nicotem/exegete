# SPDX-License-Identifier: LGPL-3.0-or-later
"""The tool descriptions Exegete serves are the committed ones.

scripts/served_texts.py renders every description of both tool sets,
`full` and `core`, and tests/fixtures/served_descriptions.txt holds the
render as it was last written and reviewed. A change to any description,
or to a paragraph several descriptions share, fails here until the dump
is written again (`python scripts/served_texts.py write`, on Python
3.13) and its diff read. Python 3.13 strips docstring indentation that
earlier versions keep, so the comparison is exact on 3.13 and sets
white space aside on any other version.
"""
import ast
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from exegete import server  # noqa: E402


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "served_texts", REPO / "scripts" / "served_texts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_served_descriptions_are_the_committed_ones(script):
    rendered = script.render()
    # Read as text, so that a checkout with Windows line ends reads the
    # same; the render itself holds none
    committed = script.DUMP.read_text(encoding="utf-8")
    assert "\r" not in rendered
    exact = sys.version_info[:2] == script.EXACT_ON
    diff = script.differences(rendered, committed, exact)
    assert not diff, "\n".join(diff + [
        "A served description differs from the dump: write the dump "
        "again with `python scripts/served_texts.py write` on Python "
        "3.13, and review its diff."])


def test_the_environment_is_pinned(script):
    environ = {"HOME": "home", "USERPROFILE": "home", "TMPDIR": "tmp",
               "UV_CACHE_DIR": "cache", "EXEGETE_TOOLSET": "core",
               "QUALCODER_MCP_TOOLSET": "core", "PATH": "bin"}
    folder = script.pin_environment(environ)
    try:
        for key in ("HOME", "USERPROFILE", "TMPDIR", "UV_CACHE_DIR"):
            assert folder in Path(environ[key]).parents, key
            assert Path(environ[key]).is_dir(), key
        assert "EXEGETE_TOOLSET" not in environ
        assert "QUALCODER_MCP_TOOLSET" not in environ
        assert environ["PATH"] == "bin"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_the_dump_is_written_on_python_3_13_alone(script):
    assert script.refusal("write", (3, 13, 5)) is None
    for version in ((3, 10, 18), (3, 11, 13), (3, 12, 0), (3, 14, 0)):
        assert script.refusal("write", version), version
    assert script.refusal("render", (3, 11, 13)) is None
    assert script.refusal("check", (3, 11, 13)) is None


# The decorator that puts shared paragraphs back into docstrings. A
# docstring as the compiler leaves it: its first line flush, the others
# indented by four spaces before Python 3.13 and by none on 3.13, which
# strips the indentation. Both forms are built as strings, so that both
# are checked on every version.
FORMS = {"indented": "    ", "flush": ""}
SHARED = "Words several tools share,\nwritten once."
OTHER = "A second paragraph\nthey share."
# "Args:" also stands inside a line before the line it starts, where it
# does not count
HEAD = ["Do one thing.", "", "What it does, before the Args: below,",
        "said here."]
TAIL = ["Args:", "    x: what it is."]


def _form(lines, indent):
    head, *rest = lines
    return "\n".join([head] + [indent + line if line else ""
                               for line in rest] + [indent])


def _held(doc, *blocks, **where):
    def tool():
        pass
    tool.__doc__ = doc
    server._with_paragraphs(*blocks, **where)(tool)
    return tool.__doc__


@pytest.mark.parametrize("indent", list(FORMS.values()), ids=list(FORMS))
def test_the_decorator_keeps_every_byte(indent):
    shared, other = SHARED.split("\n"), OTHER.split("\n")
    without = _form(HEAD + [""] + TAIL, indent)
    # A paragraph with a blank line after it
    assert _held(without, SHARED, before="Args:") == _form(
        HEAD + [""] + shared + [""] + TAIL, indent)
    # One the next line follows with no blank line
    assert _held(without, SHARED, before="Args:", gap="\n") == _form(
        HEAD + [""] + shared + TAIL, indent)
    # Two in one call, a blank line between them
    assert _held(without, SHARED, OTHER, before="Args:") == _form(
        HEAD + [""] + shared + [""] + other + [""] + TAIL, indent)


@pytest.mark.parametrize("before", ["Returns:", "does,"])
def test_a_place_no_line_starts_with_is_refused(before):
    # "Returns:" is absent; "does," has other words before it on its line
    with pytest.raises(ValueError):
        _held(_form(HEAD + [""] + TAIL, "    "), SHARED, before=before)


# The paragraphs written once in server.py, and the one place a held
# text is also typed: apply_codings gives the lock paragraph's words as
# one of its safety guarantees, in other line breaks
HELD = ("LOCK_REFUSED_PARAGRAPH", "TWO_STEP_PARAGRAPH",
        "EXPORT_FULL_MEMOS_PARAGRAPH", "CODER_VISIBILITY_COUNTS_PARAGRAPH")
ALSO_TYPED = {"LOCK_REFUSED_PARAGRAPH": {"apply_codings"}}


def _flat(text):
    return " ".join(text.split())


@pytest.fixture(scope="module")
def package():
    """Each module of the package, parsed: (its file, its tree)."""
    return [(path, ast.parse(path.read_text(encoding="utf-8")))
            for path in sorted(Path(server.__file__).parent.rglob("*.py"))]


def _typed_in(flat, package):
    """Where the package's source holds `flat`, white space set aside:
    the name of the constant, function, class or file a string belongs
    to, or the file and line of any other string."""
    places = set()
    for path, tree in package:
        names = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                names[id(node.value)] = node.targets[0].id
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)) \
                    and node.body and isinstance(node.body[0], ast.Expr):
                names[id(node.body[0].value)] = getattr(node, "name",
                                                        path.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) \
                    and isinstance(node.value, str) \
                    and flat in _flat(node.value):
                places.add(names.get(id(node),
                                     f"{path.name} line {node.lineno}"))
    return places


def _given_by_decorator(name, package):
    """The tools whose _with_paragraphs line names the constant `name`."""
    tree = next(tree for path, tree in package if path.name == "server.py")
    return {node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for deco in node.decorator_list
            if isinstance(deco, ast.Call)
            and getattr(deco.func, "id", "") == "_with_paragraphs"
            and any(getattr(arg, "id", "") == name for arg in deco.args)}


@pytest.mark.parametrize("name", HELD)
def test_each_paragraph_is_typed_once(script, package, name):
    flat = _flat(getattr(server, name))
    also = ALSO_TYPED.get(name, set())
    assert _typed_in(flat, package) == {name} | also
    given = _given_by_decorator(name, package)
    assert given
    served = {tool for tool, text in script.descriptions("full")
              if flat in _flat(text)}
    assert served == given | also
