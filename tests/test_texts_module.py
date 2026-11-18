# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: the texts server.py held as constants, and the descriptions
of its tools, prompts and resources, are in src/exegete/texts.py.

They moved there word for word: the constants first, which server.py
imports each by its name, so every use and every `server.NAME` reads the
same object as before; then the descriptions, which were the functions'
docstrings, each now `<ITS NAME IN CAPITALS>_DESCRIPTION`, written flush
and read as `texts.NAME` where the function is registered.
docs/snapshot/, unchanged by either, shows that every byte served stayed
(tests/test_served_texts.py). What this file pins:

1. texts.py holds only its docstring, its imports and its assignments,
   and imports nothing of server.py;
2. every constant texts.py assigns, the descriptions aside, is bound in
   server.py, by its one import from texts.py, to the same object, and
   server.py assigns it nowhere; no description is imported by name;
3. server.py assigns at module level no text of four words or more, as
   scripts/code_texts.py reads one, but the five no assistant receives:
   inside an `if`, `try`, `with`, `for`, `while` or `match` block too,
   by unpacking, to an item or an attribute, by a walrus (in a
   decorator, a default or a class's bases too) or as a `for`
   statement's target;
4. every function server.py registers takes its description from
   texts.py, through _with_description, its innermost decorator, with no
   docstring of its own; three give `description=`, which FastMCP takes
   in place of the docstring;
5. _with_description gives the text as written, on every Python;
6. server.py keeps no import that only a moved text read.
"""
import ast
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from exegete import server, texts  # noqa: E402

SERVER = REPO / "src" / "exegete" / "server.py"
TEXTS = REPO / "src" / "exegete" / "texts.py"
# The module-level texts that stay in server.py: no assistant receives
# them. The MCP library's four lines, as the log gets them; the notes
# written to standard error at a start (the earlier tool set's name, the
# command run at a terminal, the old command); and SQLite's own words,
# matched against its errors
STAYS = ("_LIBRARY_LINES", "LIFECYCLE_NOTE", "TTY_NOTICE", "OLD_NAME_NOTE",
         "_TRANSIENT_SQLITE_WORDS")


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _assigned(tree):
    """The names a module's top-level assignments bind, in order."""
    found = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            found += [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign):
            found.append(node.target.id)
    return found


def _code_texts():
    spec = importlib.util.spec_from_file_location(
        "code_texts", REPO / "scripts" / "code_texts.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclass looks its module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_texts_holds_its_docstring_imports_and_assignments_alone():
    tree = _tree(TEXTS)
    first, rest = tree.body[0], tree.body[1:]
    assert isinstance(first, ast.Expr) and isinstance(first.value.value, str)
    kinds = [type(node).__name__ for node in rest]
    imports = kinds.count("Import") + kinds.count("ImportFrom")
    # the imports first, then nothing but assignments
    assert set(kinds[:imports]) <= {"Import", "ImportFrom"}, kinds[:imports]
    assert set(kinds[imports:]) <= {"Assign", "AnnAssign"}, sorted(
        set(kinds[imports:]))
    for node in rest[:imports]:
        named = [alias.name for alias in node.names]
        assert "server" not in named, ast.unparse(node)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "server", ast.unparse(node)
    # every assignment binds one name, whole
    for node in rest[imports:]:
        targets = node.targets if isinstance(node, ast.Assign) \
            else [node.target]
        assert len(targets) == 1 and isinstance(targets[0], ast.Name), \
            ast.unparse(node)[:80]
    assert len(_assigned(tree)) == len(set(_assigned(tree)))


def _read_through_the_module(tree):
    """The names server.py reads as `texts.NAME`: the descriptions."""
    return {node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name) and node.value.id == "texts"}


def test_each_text_is_imported_into_server_and_assigned_there_nowhere():
    names = _assigned(_tree(TEXTS))
    tree = _tree(SERVER)
    described = _read_through_the_module(tree)
    assert described <= set(names), sorted(described - set(names))
    assert all(name.endswith("_DESCRIPTION") for name in described)
    constants = [name for name in names if name not in described]
    assert len(constants) > 300, len(constants)
    imports = [node for node in ast.walk(tree)
               if isinstance(node, ast.ImportFrom) and node.module == "texts"
               and node.level == 1]
    assert len(imports) == 1, [ast.unparse(node)[:60] for node in imports]
    aliases = imports[0].names
    assert all(alias.asname is None for alias in aliases)
    assert [alias.name for alias in aliases] == constants
    for name in constants:
        assert getattr(server, name) is getattr(texts, name), name
    # a description imported by name would sit among server.py's names,
    # where sweeps take constants by their prefix as Exegete's own words
    assert server.texts is texts
    assert sorted(described & set(vars(server))) == []
    bound = [node.id for node in ast.walk(tree)
             if isinstance(node, ast.Name)
             and isinstance(node.ctx, (ast.Store, ast.Del))]
    bound += [name for node in ast.walk(tree)
              if isinstance(node, (ast.Global, ast.Nonlocal))
              for name in node.names]
    assert sorted(set(bound) & set(names)) == []


# The definitions whose bodies the guard leaves out: a function's and a
# lambda's run only when called; a class's runs as the module is
# imported, but what it binds belongs to the class
DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
               ast.Lambda)


def _run_at_module_level(body):
    """The statements the guard reads: those of a module's body and, at
    any depth, of the `if`, `try`, `with`, `for`, `while` and `match`
    blocks there, never those of a function's or a class's body."""
    for node in body:
        yield node
        if isinstance(node, DEFINITIONS):
            continue
        for field in ("body", "orelse", "finalbody"):
            yield from _run_at_module_level(getattr(node, field, []))
        for handler in getattr(node, "handlers", []):
            yield from _run_at_module_level(handler.body)
        for case in getattr(node, "cases", []):
            yield from _run_at_module_level(case.body)


def _bound(target):
    """What an assignment's target binds: each name, unpacked too, and
    each item or attribute it sets, as the source writes it."""
    return [each.id if isinstance(each, ast.Name) else ast.unparse(each)
            for each in ast.walk(target)
            if isinstance(each, (ast.Name, ast.Subscript, ast.Attribute))
            and isinstance(each.ctx, ast.Store)]


def _own_nodes(statement):
    """The nodes of one statement that the module runs as it is
    imported: of a function's or a class's definition, its decorators,
    defaults, annotations, bases and keywords; of any other statement,
    its own expressions. Never a body, nor what is inside a lambda, nor
    the statements of a block, which _run_at_module_level gives on their
    own."""
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
        arguments = statement.args
        given = [*arguments.posonlyargs, *arguments.args,
                 *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
        start = [*statement.decorator_list, *arguments.defaults,
                 *[each for each in arguments.kw_defaults if each],
                 *[each.annotation for each in given
                   if each is not None and each.annotation is not None],
                 *([statement.returns] if statement.returns else [])]
    elif isinstance(statement, ast.ClassDef):
        start = [*statement.decorator_list, *statement.bases,
                 *statement.keywords]
    else:
        start = list(ast.iter_child_nodes(statement))
    stack = [each for each in start
             if not isinstance(each, DEFINITIONS + (ast.stmt,))]
    while stack:
        node = stack.pop()
        yield node
        stack += [child for child in ast.iter_child_nodes(node)
                  if not isinstance(child, DEFINITIONS + (ast.stmt,))]


def _holders(tree):
    """Each place at module level where a value is bound, as (first line,
    last line, what it binds): an assignment, whole; a `for` statement's
    iterable, which binds its target; a walrus anywhere in a statement."""
    for node in _run_at_module_level(tree.body):
        if isinstance(node, ast.Assign):
            yield (node.lineno, node.end_lineno,
                   [name for target in node.targets
                    for name in _bound(target)])
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            yield node.lineno, node.end_lineno, _bound(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            yield (node.iter.lineno, node.iter.end_lineno,
                   _bound(node.target))
        for each in _own_nodes(node):
            if isinstance(each, ast.NamedExpr):
                yield each.lineno, each.end_lineno, _bound(each.target)


def test_server_assigns_no_text_but_those_no_assistant_receives():
    """Inside an `if` or a `try` block too, and by unpacking (the review
    of the constants' move, finding 1); inside a `match` case, to an item
    or an attribute, by a walrus, in a definition's decorators, defaults
    and bases too, and as a `for` statement's target (the review of the
    descriptions' move, finding 3, and the review of that change)."""
    holders = list(_holders(_tree(SERVER)))
    holding = set()
    for text in _code_texts().code_texts(REPO):
        if text.module != "src/exegete/server.py" or text.docstring \
                or text.raw:
            continue
        holding |= {name for first, last, names in holders
                    if first <= text.line <= last for name in names}
    assert sorted(holding - set(STAYS)) == [], (
        "a text of four words or more assigned in server.py: write it in "
        "texts.py, which server.py imports it from")
    # each of the five is still there, so the list stays true
    assert sorted(set(STAYS) - holding) == []


REGISTERING = ("mcp.tool", "mcp.prompt", "mcp.resource")
# The three whose registration gives `description=`, which FastMCP takes
# in place of a docstring: each with the description it gives
DESCRIBED_AT_REGISTRATION = {
    "read_brief": "texts.READ_BRIEF_DESCRIPTION",
    "get_methods_guidance": "texts.GET_METHODS_GUIDANCE_DESCRIPTION",
    "get_brief": "texts.GET_BRIEF_DESCRIPTION"}


def _registered(tree):
    """Each function server.py registers, with its registering call."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and \
                        ast.unparse(decorator.func) in REGISTERING:
                    yield node, decorator


def _given():
    """Each function given its description by _with_description, with
    the name of that description in texts.py."""
    given = {}
    for node, _ in _registered(_tree(SERVER)):
        last = node.decorator_list[-1]
        if isinstance(last, ast.Call) and \
                ast.unparse(last.func) == "_with_description":
            given[node.name] = ast.unparse(last.args[0])
    return given


def test_every_description_is_given_from_texts():
    given = _given()
    registered = list(_registered(_tree(SERVER)))
    assert len(registered) == len(given) + len(DESCRIBED_AT_REGISTRATION)
    for node, registration in registered:
        keywords = {keyword.arg: ast.unparse(keyword.value)
                    for keyword in registration.keywords}
        if node.name in DESCRIBED_AT_REGISTRATION:
            assert keywords.get("description") == \
                DESCRIBED_AT_REGISTRATION[node.name], node.name
            continue
        assert "description" not in keywords, node.name
        # no docstring: _with_description refuses a function that has one
        assert ast.get_docstring(node, clean=False) is None, node.name
        assert given[node.name] == \
            f"texts.{node.name.upper()}_DESCRIPTION", node.name
        assert len(node.decorator_list[-1].args) == 1, node.name
    # each description given once, and each one texts.py holds
    names = set(_assigned(_tree(TEXTS)))
    assert len(set(given.values())) == len(given)
    assert {value.split(".", 1)[1] for value in given.values()} <= names


def test_a_function_with_a_docstring_is_refused():
    def tool():
        """A docstring."""
    with pytest.raises(ValueError):
        server._with_description("A description.")(tool)


# Python versions as `sys.version_info` gives them, the oldest Exegete
# supports and the newest the suite runs on among them
VERSIONS = {"3.11": (3, 11, 13, "final", 0), "3.12": (3, 12, 12, "final", 0),
            "3.13": (3, 13, 5, "final", 0), "3.14": (3, 14, 0, "final", 0)}
# Made-up descriptions: one line; blank lines; lines indented further, as
# an argument under "Args:"; and a last line with text on it
MADE_UP = {
    "one line": "One line.",
    "blank lines": "First.\n\nThird, after a blank line.\n\nFifth.\n",
    "lines indented further": (
        "Do one thing.\n\nArgs:\n    x: what it is,\n        over two "
        "lines.\n"),
    "text on the last line": "First.\nSecond, after it nothing.",
}


@pytest.mark.parametrize("version", list(VERSIONS.values()),
                         ids=list(VERSIONS))
def test_each_description_is_given_as_written_on_every_python(
        monkeypatch, version):
    """The owner's ruling of 17 November 2026: Python 3.11 and 3.12 send
    each description as 3.13 does, without the indentation of the source
    that they kept while the descriptions were docstrings. Each Python
    is the one sys.version_info names; the suite's jobs on 3.11 also
    hold docs/snapshot/ to it exactly (tests/test_served_texts.py)."""
    names = [value.split(".", 1)[1] for value in _given().values()]
    texts_given = [getattr(texts, name) for name in names]
    texts_given += list(MADE_UP.values())
    given = []
    with monkeypatch.context() as patch:
        patch.setattr(sys, "version_info", version)
        for text in texts_given:
            def tool():
                pass
            server._with_description(text)(tool)
            given.append(tool.__doc__)
    assert given == texts_given


def test_server_keeps_no_import_the_move_left_behind():
    """A name texts.py imports for its texts, which server.py imports
    too, is read in server.py: an import there that only a moved text
    read went with it (the review of the constants' move, finding 4:
    SECRET_UNAVAILABLE_MESSAGE, read by TOKEN_ERROR_TEXTS alone)."""
    def imported(tree):
        return {(alias.asname or alias.name).split(".")[0]
                for node in tree.body
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names}
    server_tree = _tree(SERVER)
    read = {node.id for node in ast.walk(server_tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    both = imported(_tree(TEXTS)) & imported(server_tree)
    assert both, "texts.py and server.py share no import: read again"
    assert sorted(both - read) == []
