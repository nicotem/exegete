# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5: the texts Exegete serves that are written once, as
constants, are in src/exegete/texts.py.

They moved there word for word from server.py, which imports each by its
name, so every use and every `server.NAME` reads the same object as
before; docs/snapshot/, unchanged, shows that every byte served stayed
(tests/test_served_texts.py). What this file pins:

1. texts.py holds only its docstring, its imports and its assignments,
   and imports nothing of server.py;
2. every name texts.py assigns is bound in server.py, by its one import
   from texts.py, to the same object, and server.py assigns it nowhere;
3. server.py assigns at module level no text of four words or more, as
   scripts/code_texts.py reads one, but the five no assistant receives.
"""
import ast
import importlib.util
import sys
from pathlib import Path

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


def test_each_text_is_imported_into_server_and_assigned_there_nowhere():
    names = _assigned(_tree(TEXTS))
    assert len(names) > 300, len(names)
    tree = _tree(SERVER)
    imports = [node for node in ast.walk(tree)
               if isinstance(node, ast.ImportFrom) and node.module == "texts"
               and node.level == 1]
    assert len(imports) == 1, [ast.unparse(node)[:60] for node in imports]
    aliases = imports[0].names
    assert all(alias.asname is None for alias in aliases)
    assert [alias.name for alias in aliases] == names
    for name in names:
        assert getattr(server, name) is getattr(texts, name), name
    bound = [node.id for node in ast.walk(tree)
             if isinstance(node, ast.Name)
             and isinstance(node.ctx, (ast.Store, ast.Del))]
    bound += [name for node in ast.walk(tree)
              if isinstance(node, (ast.Global, ast.Nonlocal))
              for name in node.names]
    assert sorted(set(bound) & set(names)) == []


def test_server_assigns_no_text_but_those_no_assistant_receives():
    tree = _tree(SERVER)
    statements = [(node.lineno, node.end_lineno, node) for node in tree.body
                  if isinstance(node, (ast.Assign, ast.AnnAssign))]
    holding = set()
    for text in _code_texts().code_texts(REPO):
        if text.module != "src/exegete/server.py" or text.docstring \
                or text.raw:
            continue
        holding |= {name for first, last, node in statements
                    if first <= text.line <= last
                    for name in _assigned(ast.Module([node], []))}
    assert sorted(holding - set(STAYS)) == [], (
        "a text of four words or more assigned in server.py: write it in "
        "texts.py, which server.py imports it from")
    # each of the five is still there, so the list stays true
    assert sorted(set(STAYS) - holding) == []
