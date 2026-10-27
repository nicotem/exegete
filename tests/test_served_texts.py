# SPDX-License-Identifier: LGPL-3.0-or-later
"""What Exegete sends the assistant is the snapshot committed in
docs/snapshot/.

scripts/served_texts.py renders, for each tool set, `full` and `core`,
everything Exegete sends the assistant before a project is open (the
opening text, every tool's entry, the prompts, the resources and their
templates, the guidance texts) and read_brief's answer, with the sizes
the documents round; docs/snapshot/ holds the render as it was last
written and reviewed. A change to any of these texts fails here until
the snapshot is written again (`python scripts/served_texts.py write`,
on Python 3.13) and its diff read. Python 3.13 strips docstring
indentation that earlier versions keep, so the comparison is exact on
3.13 and sets white space aside on any other version, where the
documents' "about five per cent more" is held instead.

Also here: the decorator that puts a paragraph several descriptions
share back into each of them, and each such paragraph typed once.
"""
import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from exegete import server  # noqa: E402

# The home folder this process started with, the one exegete.server was
# imported under (the suite moves the home folder for each test)
HOME_AT_IMPORT = Path.home()


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "served_texts", REPO / "scripts" / "served_texts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exact(script):
    return sys.version_info[:2] == script.EXACT_ON


def test_the_committed_snapshot_is_what_the_code_serves(script):
    files = script.snapshot()
    # The render holds no Windows line end; the committed files are read
    # as text, so a checkout with Windows line ends reads the same
    assert not any("\r" in text for text in files.values())
    found = script.compare(files, script.committed(), _exact(script))
    assert not found, "\n".join(found + [
        "What Exegete serves differs from docs/snapshot/: regenerate with "
        "`python scripts/served_texts.py write` on Python 3.13 and review "
        "the diff."])


# Each kind of text the snapshot holds, changed as a change to the code
# would change it, and the sets whose files then differ
def _a_description(monkeypatch):
    monkeypatch.setitem(server.mcp.original_descriptions, "read_brief",
                        "A description changed.")


def _an_input_schema(monkeypatch):
    tool = server.mcp._tool_manager._tools["read_brief"]
    monkeypatch.setitem(tool.parameters, "description", "Changed.")


def _an_output_schema(monkeypatch):
    tool = server.mcp._tool_manager._tools["read_brief"]
    monkeypatch.setitem(tool.fn_metadata.output_schema, "description",
                        "Changed.")


def _an_annotation(monkeypatch):
    tool = server.mcp._tool_manager._tools["read_brief"]
    monkeypatch.setattr(tool, "annotations", tool.annotations.model_copy(
        update={"title": "An annotation changed"}))


def _a_mark_under_meta(monkeypatch):
    monkeypatch.setitem(server.TOOL_META, "read_brief",
                        {"exegete/changed": True})


def _the_opening_text(monkeypatch):
    # through the constant: every set's apply writes the served one again
    monkeypatch.setattr(server, "SERVER_INSTRUCTIONS",
                        "An opening text changed.")


def _the_brief(monkeypatch):
    monkeypatch.setattr(server, "BRIEF_FULL", "A brief changed.")


def _prompt(monkeypatch, field, value):
    monkeypatch.setattr(server.mcp._prompt_manager._prompts[
        "summarize_project"], field, value)


def _a_resource(monkeypatch):
    monkeypatch.setattr(server.mcp._resource_manager._resources[
        "exegete://project/info"], "description", "Changed.")


def _a_template(monkeypatch):
    monkeypatch.setattr(server.mcp._resource_manager._templates[
        "exegete://codes/{code_id}"], "description", "Changed.")


def _the_methods_notes(monkeypatch):
    monkeypatch.setattr(server, "METHODS_GUIDANCE", "Notes changed.")


def _core_s_mark(monkeypatch):
    monkeypatch.setattr(server, "NOT_IN_THIS_TOOL_SET", " (not here)")


BOTH = ("full", "core")
KINDS = {
    "a tool's description": (_a_description, BOTH),
    "an input schema": (_an_input_schema, BOTH),
    "an output schema": (_an_output_schema, BOTH),
    "an annotation": (_an_annotation, BOTH),
    "a mark under _meta": (_a_mark_under_meta, BOTH),
    "the opening text": (_the_opening_text, BOTH),
    "the brief": (_the_brief, BOTH),
    "a prompt's description": (
        lambda patch: _prompt(patch, "description", "Changed."), BOTH),
    "a prompt's text": (
        lambda patch: _prompt(patch, "fn", lambda: "A text changed."), BOTH),
    "a resource's description": (_a_resource, BOTH),
    "a template's description": (_a_template, BOTH),
    "the methods notes": (_the_methods_notes, BOTH),
    "core's mark on a tool it lacks": (_core_s_mark, ("core",)),
}


@pytest.fixture(scope="module")
def rendered(script):
    return {mode: script.render(mode) for mode in script.SETS}


@pytest.mark.parametrize("kind", list(KINDS))
def test_each_kind_of_text_is_compared(script, rendered, monkeypatch, kind):
    change, changed = KINDS[kind]
    change(monkeypatch)
    for mode in script.SETS:
        now = script.render(mode)
        assert (now != rendered[mode]) == (mode in changed), (kind, mode)
        # and with white space set aside, as on another Python version
        assert bool(script.differences(now, rendered[mode], False)) == (
            mode in changed), (kind, mode)


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


def test_the_snapshot_is_written_on_python_3_13_alone(script):
    assert script.refusal("write", (3, 13, 5)) is None
    for version in ((3, 10, 18), (3, 11, 13), (3, 12, 0), (3, 14, 0)):
        assert "Python 3.13" in script.refusal("write", version), version
    assert script.refusal("check", (3, 11, 13)) is None


def _write(out, home, seed, cwd):
    """The script's `write` in a process of its own, HOME and USERPROFILE
    given, and its hash seed."""
    environ = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   PYTHONHASHSEED=str(seed))
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "served_texts.py"), "write",
         "--out", str(out)], env=environ, cwd=str(cwd), capture_output=True,
        text=True, encoding="utf-8", timeout=600)


def _reported(stderr, what):
    found = re.search(rf"^{what} folder for this run: (.+)$", stderr, re.M)
    assert found, stderr
    return Path(found.group(1).strip())


def test_two_runs_write_the_same_files(script, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    outs = [tmp_path / "first", tmp_path / "second"]
    runs = [_write(out, home, seed, tmp_path)
            for out, seed in zip(outs, (1, 2))]
    if not _exact(script) or script.library_refusal():
        # Another Python, or other releases of mcp or pydantic than the
        # lock's: nothing written
        for run, out in zip(runs, outs):
            assert run.returncode == 2, run.stderr
            assert "Not written" in run.stderr
            assert not out.exists() or not any(out.iterdir())
        return
    for run in runs:
        assert run.returncode == 0, run.stderr
        # the folders the run pinned: not the home given, and gone
        for what in ("Home", "Temporary"):
            folder = _reported(run.stderr, what)
            assert folder != home and home not in folder.parents, what
            assert script.FOLDER_PREFIX in str(folder), what
            assert not folder.exists(), what
    assert list(home.iterdir()) == []
    written = script.committed()
    for name in script.FILES:
        first, second = ((out / name).read_bytes() for out in outs)
        assert first == second, name
        assert (outs[0] / name).read_text(encoding="utf-8") == \
            written[name], name


@pytest.mark.parametrize("library", ["mcp", "pydantic"])
def test_write_stops_on_other_libraries(script, monkeypatch, capsys,
                                        tmp_path, library):
    real = script.installed
    monkeypatch.setattr(script, "installed", lambda name: "0.0.1"
                        if name == library else real(name))
    locked = ", ".join(sorted(script.locked(library)))
    reason = script.library_refusal()
    assert f"{library} 0.0.1 is installed" in reason
    assert f"uv.lock gives {library} {locked}" in reason
    # Through the command, in this process: nothing pinned, nothing
    # written
    monkeypatch.setattr(script, "pin_environment",
                        lambda environ=None: pytest.fail("pinned"))
    out = tmp_path / "out"
    assert script.main(["write", "--out", str(out)]) == 2
    assert not out.exists()
    if _exact(script):
        assert reason in capsys.readouterr().err


def test_no_path_of_this_computer_is_in_the_snapshot(script):
    places = {Path.home(), HOME_AT_IMPORT, REPO, Path(tempfile.gettempdir()),
              Path(sys.prefix)}
    places |= {place.resolve() for place in places}
    forms = {form for place in places for form in (
        place.as_posix(), str(PureWindowsPath(place)), str(place))
        if len(form) > 3}
    texts = dict(script.snapshot())
    texts.update({f"committed {name}": text for name, text
                  in script.committed().items() if text is not None})
    for name, text in texts.items():
        assert [form for form in forms if form in text] == [], name
        # the folder the script pins its home and temporary folder in
        assert script.FOLDER_PREFIX not in text, name


def test_the_registry_is_as_it_was_after_a_render(script):
    tools = server.mcp._tool_manager._tools
    before = list(tools.items())
    opening = server.mcp._mcp_server.instructions
    first = script.render("full")
    script.render("core")
    assert [name for name in tools] == [name for name, _ in before]
    assert all(tools[name] is tool for name, tool in before)
    assert server.mcp._mcp_server.instructions == opening
    assert script.render("full") == first


NUMBERS = ("one", "two", "three", "four", "five", "six", "seven", "eight",
           "nine", "ten")
# Where the documents give the per cent the earlier versions add
PER_CENT = {"README.md": r"about (\w+) per cent more on 3\.10 to 3\.12",
            "TOOLS.md": r"definitions measure about (\w+) per cent more"}


@pytest.mark.skipif(sys.version_info[:2] >= (3, 13),
                    reason="the per cent is Python 3.10 to 3.12's")
def test_the_per_cent_below_3_13_is_the_documents(script):
    sizes = json.loads(script.committed()["sizes.json"])
    stated = set()
    for name, pattern in PER_CENT.items():
        text = (REPO / name).read_text(encoding="utf-8")
        found = re.search(pattern, " ".join(text.replace("\n>", " ").split()))
        assert found, name
        stated.add(NUMBERS.index(found.group(1)) + 1)
    assert len(stated) == 1, stated
    for mode in script.SETS:
        now = script.measure(script.served(mode))[
            "tool_definitions_characters"]
        then = sizes[mode]["tool_definitions_characters"]
        assert round(100 * (now / then - 1)) in stated, (mode, now, then)


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


def _decorated(tree):
    """Each function of a parsed module with a _with_paragraphs line, and
    the names that line passes."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if isinstance(deco, ast.Call) and getattr(
                        deco.func, "id", "") == "_with_paragraphs":
                    yield node.name, {arg.id for arg in deco.args
                                      if isinstance(arg, ast.Name)}


# The paragraphs written once in server.py, read from its
# _with_paragraphs lines, so that a constant a later change passes there
# is checked too; and the one place a held text is also typed:
# apply_codings gives the lock paragraph's words as one of its safety
# guarantees, in other line breaks
SERVER_TREE = ast.parse((REPO / "src" / "exegete" / "server.py").read_text(
    encoding="utf-8"))
HELD = sorted(set().union(*(names for _, names in _decorated(SERVER_TREE))))
ALSO_TYPED = {"LOCK_REFUSED_PARAGRAPH": {"apply_codings"}}


def test_the_held_paragraphs_are_read_from_the_decorator_lines():
    assert HELD
    assert set(ALSO_TYPED) <= set(HELD)
    assert all(isinstance(getattr(server, name), str) for name in HELD)


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


@pytest.mark.parametrize("name", HELD)
def test_each_paragraph_is_typed_once(script, package, name):
    flat = _flat(getattr(server, name))
    also = ALSO_TYPED.get(name, set())
    assert _typed_in(flat, package) == {name} | also
    given = {tool for tool, names in _decorated(SERVER_TREE)
             if name in names}
    assert given
    served = {entry["name"] for entry in script.served("full")["tools"]
              if flat in _flat(entry.get("description", ""))}
    assert served == given | also
