# SPDX-License-Identifier: LGPL-3.0-or-later
"""Write out the tool descriptions Exegete serves, to compare them.

    python scripts/served_texts.py render    print them
    python scripts/served_texts.py write     save them as the dump
    python scripts/served_texts.py check     compare them with the dump

For each tool set, `full` and then `core`, every tool in the order
tools/list gives: a line "### <set> <tool>", then its description as
Exegete serves it, verbatim. The dump is
tests/fixtures/served_descriptions.txt, which tests/test_served_texts.py
compares with a fresh render, so a change to a description, or to a
paragraph several descriptions share, is read as a diff of that file:
write it again when a description changes, and review the diff.

Python 3.13 strips the indentation of docstrings when it compiles them,
and earlier versions keep it, so the dump is written on Python 3.13
alone, the only version compared exactly; on any other the comparison
sets white space aside.

Before importing Exegete, the script points HOME, USERPROFILE, TMPDIR
and UV_CACHE_DIR at a new temporary folder, removed at exit, and drops
every EXEGETE_ and QUALCODER_ setting, so that nothing of this
computer's reaches the texts and nothing is written in its home folder.
Run it in the development install (CONTRIBUTING.md, step 3): it stops
when the exegete it imports is not this repository's.
"""
import asyncio
import atexit
import difflib
import itertools
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DUMP = REPO / "tests" / "fixtures" / "served_descriptions.txt"
SETS = ("full", "core")
PINNED = ("HOME", "USERPROFILE", "TMPDIR", "UV_CACHE_DIR")
DROPPED = ("EXEGETE_", "QUALCODER_")
EXACT_ON = (3, 13)
USAGE = "usage: python scripts/served_texts.py render | write | check"


def pin_environment(environ=os.environ):
    """Point HOME, USERPROFILE, TMPDIR and UV_CACHE_DIR at folders of a
    new temporary folder, removed at exit, and drop every EXEGETE_ and
    QUALCODER_ setting from `environ`. Returns the folder."""
    folder = Path(tempfile.mkdtemp(prefix="exegete-served-texts-"))
    atexit.register(shutil.rmtree, folder, ignore_errors=True)
    for key in PINNED:
        (folder / key.lower()).mkdir()
        environ[key] = str(folder / key.lower())
    for key in [key for key in environ if key.startswith(DROPPED)]:
        del environ[key]
    if environ is os.environ:
        tempfile.tempdir = None  # so that TMPDIR is read again
    return folder


def descriptions(mode):
    """(tool, description) for every tool the set `mode` serves, in the
    order tools/list gives. The registry and the opening text are put
    back from a copy afterwards, in their order: putting back only the
    tools a set removed would move them to the registry's end."""
    from exegete import server
    tools = server.mcp._tool_manager._tools
    before, opening = dict(tools), server.mcp._mcp_server.instructions
    server._apply_toolset(mode)
    try:
        listed = asyncio.run(server.mcp.list_tools())
        return [(tool.name, tool.description or "") for tool in listed]
    finally:
        tools.clear()
        tools.update(before)
        server.mcp._mcp_server.instructions = opening


def render():
    """The dump's text: each set's descriptions, each under its line."""
    return "".join(f"### {mode} {name}\n{text}\n"
                   for mode in SETS for name, text in descriptions(mode))


def differences(rendered, committed, exact):
    """The first lines of a diff from the dump to a render, none when
    they agree: line by line when `exact`, otherwise word by word, white
    space set aside."""
    if exact:
        if rendered == committed:
            return []
        old, new = committed.split("\n"), rendered.split("\n")
    else:
        old, new = committed.split(), rendered.split()
        if old == new:
            return []
    diff = difflib.unified_diff(old, new, "dump", "served", n=2,
                                lineterm="")
    return list(itertools.islice(diff, 40))


def refusal(command, version):
    """Why `command` cannot run on this Python version, or None."""
    if command == "write" and tuple(version[:2]) != EXACT_ON:
        return (f"Not written: the dump is written on Python 3.13 alone, "
                f"the only version compared exactly, and this is "
                f"{version[0]}.{version[1]}.")
    return None


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1 or args[0] not in ("render", "write", "check"):
        print(USAGE, file=sys.stderr)
        return 2
    command = args[0]
    reason = refusal(command, sys.version_info)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    pin_environment()
    import exegete
    source = Path(exegete.__file__).resolve()
    if (REPO / "src").resolve() not in source.parents:
        print(f"Stopped: exegete is imported from {source}, not from this "
              f"repository's src/; install the repository for development "
              f"(CONTRIBUTING.md, step 3).", file=sys.stderr)
        return 2
    text = render()
    if command == "render":
        sys.stdout.buffer.write(text.encode("utf-8"))
        return 0
    if command == "write":
        DUMP.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {DUMP.relative_to(REPO)}.", file=sys.stderr)
        return 0
    exact = tuple(sys.version_info[:2]) == EXACT_ON
    lines = differences(text, DUMP.read_text(encoding="utf-8"), exact)
    print("\n".join(lines) or "The descriptions are the dump's.")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
