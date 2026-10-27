#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""The texts Exegete's code holds, read from its source (v0.15.2).

    python scripts/code_texts.py [root]    each text: file:line: its start

The one reader of these texts: the facts check (tests/test_v0151_facts.py)
holds the releases they name to the plan (scripts/release_plan.py), and
the texts check reads them through this module too, with filters of its
own. Every module under src/exegete is read by Python's parser and never
imported, so reading runs none of the package's code.

What is read:
- every string constant of four words or more, wherever it stands: a
  module constant, a dictionary's value, a text built inside a function;
  adjacent literals are one constant, as the parser joins them. A word is
  a run of characters between white space with a letter in it;
- the docstring of each function decorated `mcp.tool`, `mcp.prompt` or
  `mcp.resource`, which FastMCP serves as its description; no other
  docstring;
- an f-string, whole: a value written `{names.X}` reads as the string
  constant X of names.py (so "until {names.OLD_SPELLINGS_UNTIL}" reads
  "until v1.0"), any other value as GAP, which ends no sentence; its
  literal parts are not read again on their own.
Each text carries its module and the line its first literal starts on;
one triple-quoted literal keeps its lines (its nth line is that line + n).
Standard library only.
"""

from __future__ import annotations

import ast
import functools
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PACKAGE = "src/exegete"
NAMES_MODULE = "names.py"
# What an f-string's value reads as, when it is not one of names.py's texts
GAP = "{}"
MIN_WORDS = 4
# The decorators whose functions' docstrings FastMCP serves
SERVED = frozenset({"mcp.tool", "mcp.prompt", "mcp.resource"})
TRIPLE_QUOTED = re.compile(r"[rRbBuUfF]{0,2}(?:\"\"\"|''')")
RAW = re.compile(r"[bBuUfF]?[rR]")
DEFINITIONS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class CodeText:
    module: str           # its file under the root: "src/exegete/server.py"
    line: int             # the line its first literal starts on
    text: str
    keeps_lines: bool     # one triple-quoted literal: line + n is its nth line
    docstring: bool       # a served docstring (read whatever its length)
    raw: bool             # its first literal is a raw string
    call: Optional[str]   # the call it stands in, as written ("logger.info")
    name: Optional[str]   # the module-level name it is assigned to whole


def word_count(text: str) -> int:
    return sum(1 for word in text.split() if re.search(r"[^\W\d_]", word))


def _dotted(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        before = _dotted(node.value)
        return None if before is None else f"{before}.{node.attr}"
    return None


def _assigned(tree: ast.Module) -> Dict[ast.AST, str]:
    """The values the module assigns to one name each, with that name."""
    found = {}
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        if (len(targets) == 1 and isinstance(targets[0], ast.Name)
                and node.value is not None):
            found[node.value] = targets[0].id
    return found


def _served(definition: ast.AST) -> bool:
    return isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)) \
        and any(_dotted(decorator.func if isinstance(decorator, ast.Call)
                        else decorator) in SERVED
                for decorator in definition.decorator_list)


def _fstring(node: ast.JoinedStr, names: Dict[str, str]) -> str:
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(str(value.value))
            continue
        named = value.value
        parts.append(names[named.attr] if (
            isinstance(named, ast.Attribute)
            and _dotted(named.value) == "names" and named.attr in names
            and value.conversion == -1 and value.format_spec is None)
            else GAP)
    return "".join(parts)


@functools.lru_cache(maxsize=None)
def _texts(module: str, source: str,
           names: Tuple[Tuple[str, str], ...]) -> Tuple[CodeText, ...]:
    tree, lines = ast.parse(source), source.encode("utf-8").split(b"\n")
    constants, assigned = dict(names), _assigned(tree)
    found, served, unserved = [], set(), set()
    # depth first, each node with the call it stands in, as written
    stack = [(tree, None)]
    while stack:
        node, call = stack.pop()
        if isinstance(node, DEFINITIONS) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                (served if _served(node) else unserved).add(first.value)
        if isinstance(node, ast.JoinedStr):
            text = _fstring(node, constants)
            # its values may hold texts of their own; never its parts
            stack.extend((value.value, call) for value in node.values
                         if isinstance(value, ast.FormattedValue))
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, str) or node in unserved:
                continue
            text = node.value
        else:
            inner = (_dotted(node.func) or call) if isinstance(
                node, ast.Call) else call
            stack.extend((child, call if isinstance(node, ast.Call)
                          and child is node.func else inner)
                         for child in ast.iter_child_nodes(node))
            continue
        docstring = node in served
        if not docstring and word_count(text) < MIN_WORDS:
            continue
        start = lines[node.lineno - 1][node.col_offset:].decode("utf-8")
        found.append(CodeText(
            module, node.lineno, text,
            bool(TRIPLE_QUOTED.match(start))
            and node.end_lineno - node.lineno == text.count("\n"),
            docstring, bool(RAW.match(start)), call, assigned.get(node)))
    return tuple(sorted(found, key=lambda text: (text.line, text.text)))


def code_texts(root: Path) -> List[CodeText]:
    """The texts of every module under root/src/exegete, module by module
    and line by line. A root without that folder raises
    FileNotFoundError: a check given the wrong folder must fail, never
    pass with no texts read."""
    package = Path(root) / PACKAGE
    if not package.is_dir():
        raise FileNotFoundError(
            f"{package}: no such folder; give the repository's root")
    names: Tuple[Tuple[str, str], ...] = ()
    if (package / NAMES_MODULE).is_file():
        names = tuple(sorted(
            (name, value.value) for value, name in _assigned(ast.parse(
                (package / NAMES_MODULE).read_text(encoding="utf-8"))).items()
            if isinstance(value, ast.Constant)
            and isinstance(value.value, str)))
    found: List[CodeText] = []
    for path in sorted(package.rglob("*.py")):
        found += _texts(path.relative_to(root).as_posix(),
                        path.read_text(encoding="utf-8"), names)
    return found


if __name__ == "__main__":
    try:
        read = code_texts(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    except FileNotFoundError as error:
        sys.exit(str(error))
    for each in read:
        print(f"{each.module}:{each.line}: {' '.join(each.text.split())[:90]}")
