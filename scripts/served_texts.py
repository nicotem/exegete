# SPDX-License-Identifier: LGPL-3.0-or-later
"""Write out what Exegete sends the assistant before a project is open,
and the brief, to read a change to it as a diff.

    python scripts/served_texts.py write [--out FOLDER]
    python scripts/served_texts.py check

Before a project is open, Exegete sends the assistant its opening text;
its tools, each with its description, the schemas of its arguments and
of its answer, its annotations and the marks under `_meta`; its prompts;
and its resources and resource templates. read_brief answers with the
brief. For each tool set, `full` and then `core`, `write` puts all of
it, as the protocol carries it, in docs/snapshot/full.txt and
docs/snapshot/core.txt, with the prompts' texts (each argument "X") and
the two guidance resources' texts, and the sizes the documents round in
docs/snapshot/sizes.json. tests/test_served_texts.py compares the three
files with what the code serves, so a change to any of these texts is
read as a diff of the files: write them again when a text changes, and
review the diff. Left out: the version in the handshake, so that a new
release changes nothing here, and the help tool's answers, which are
answers to a call.

Python 3.13 strips the indentation of docstrings that earlier versions
keep, and the schemas come from the mcp and pydantic libraries, so
`write` runs on Python 3.13 alone, with the releases of both that
uv.lock gives; elsewhere it writes nothing. `check` runs on any version:
exactly on 3.13, and on any other with white space set aside and the
tool counts alone of sizes.json.

Before importing Exegete, the script points HOME, USERPROFILE, TMPDIR
and UV_CACHE_DIR at a new temporary folder, removed at exit, and drops
every EXEGETE_ and QUALCODER_ setting, so that nothing of this
computer's reaches the texts and nothing is written in its home folder;
it says on standard error which home and temporary folder it used. Run
it in the development install (CONTRIBUTING.md, step 3): it stops when
the exegete it imports is not this repository's.
"""
import argparse
import asyncio
import atexit
import difflib
import importlib.metadata
import itertools
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO / "docs" / "snapshot"
SETS = ("full", "core")
FILES = tuple(f"{mode}.txt" for mode in SETS) + ("sizes.json",)
PINNED = ("HOME", "USERPROFILE", "TMPDIR", "UV_CACHE_DIR")
DROPPED = ("EXEGETE_", "QUALCODER_")
# The start of the name of the folder the environment is pinned to
FOLDER_PREFIX = "exegete-served-texts-"
EXACT_ON = (3, 13)
LIBRARIES = ("mcp", "pydantic")
MEASURED_ON = "Python 3.13, the libraries of uv.lock"
COUNTED = ("Characters, as Python counts them. tool_definitions_characters: "
           "json.dumps, with Python's defaults, of the list of every tool's "
           "name, description and input schema, in the order tools/list "
           "gives (TOOLS.md, the tool sets); definition_characters: one "
           "tool's entry in that list, alone.")
HEADER = ("Everything Exegete sends the assistant in the tool set `{mode}` "
          "before a project is\nopen, as the protocol carries it, and "
          "read_brief's answer. Written by\nscripts/served_texts.py on "
          "Python 3.13 with the libraries of uv.lock: write\nit again with "
          "that script rather than edit it.\n\n")


def pin_environment(environ=os.environ):
    """Point HOME, USERPROFILE, TMPDIR and UV_CACHE_DIR at folders of a
    new temporary folder, removed at exit, and drop every EXEGETE_ and
    QUALCODER_ setting from `environ`. Returns the folder."""
    folder = Path(tempfile.mkdtemp(prefix=FOLDER_PREFIX))
    atexit.register(shutil.rmtree, folder, ignore_errors=True)
    for key in PINNED:
        (folder / key.lower()).mkdir()
        environ[key] = str(folder / key.lower())
    for key in [key for key in environ if key.startswith(DROPPED)]:
        del environ[key]
    if environ is os.environ:
        tempfile.tempdir = None  # so that TMPDIR is read again
    return folder


def _entry(item):
    """An item as the protocol carries it."""
    return item.model_dump(by_alias=True, mode="json", exclude_none=True)


def _text(blocks):
    return "\n".join(block.text for block in blocks)


async def _gather(server):
    from mcp.shared.memory import create_connected_server_and_client_session
    from exegete import names
    guidance = f"{names.RESOURCE_SCHEME}://guidance/"
    low = server.mcp._mcp_server
    async with create_connected_server_and_client_session(low) as client:
        got = {"opening": low.create_initialization_options().instructions
               or "",
               "tools": [_entry(tool)
                         for tool in (await client.list_tools()).tools],
               "brief": _text((await client.call_tool("read_brief", {}))
                              .content),
               "prompts": [], "guidance": []}
        for prompt in (await client.list_prompts()).prompts:
            arguments = {each.name: "X" for each in prompt.arguments or []}
            messages = (await client.get_prompt(prompt.name,
                                                arguments)).messages
            got["prompts"].append((_entry(prompt), _text(
                message.content for message in messages)))
        resources = (await client.list_resources()).resources
        got["resources"] = [_entry(resource) for resource in resources]
        for resource in resources:
            if str(resource.uri).startswith(guidance):
                got["guidance"].append((str(resource.uri), _text(
                    (await client.read_resource(resource.uri)).contents)))
        got["templates"] = [_entry(template) for template in (
            await client.list_resource_templates()).resourceTemplates]
        return got


def served(mode):
    """What the set `mode` sends the assistant before a project is open,
    through an MCP session in memory, as a host's requests take it:
    the opening text, every tool's entry, read_brief's answer, every
    prompt's entry and text, the resources' and the templates' entries,
    and the guidance resources' texts. The registry and the opening text
    are put back from a copy afterwards, in their order: putting back
    only the tools a set removed would move them to the registry's end,
    and a later set would list them in another order."""
    from exegete import server
    tools = server.mcp._tool_manager._tools
    before, opening = dict(tools), server.mcp._mcp_server.instructions
    server._apply_toolset(mode)
    try:
        return asyncio.run(_gather(server))
    finally:
        tools.clear()
        tools.update(before)
        server.mcp._mcp_server.instructions = opening


def _block(title, text):
    return f"==== {title} ====\n{text}\n\n"


def _rest(title, entry):
    """An entry's other fields, its description set apart, as JSON."""
    return _block(title, json.dumps(
        {key: value for key, value in entry.items() if key != "description"},
        indent=2, ensure_ascii=False))


def _described(kind, entry, key):
    name = f"{kind} {entry[key]}"
    return (_block(f"{name}: its description", entry.get("description", ""))
            + _rest(f"{name}: the rest of its entry", entry))


def render(mode, got=None):
    """The text of docs/snapshot/<mode>.txt: under a line of its own,
    each text verbatim, and each entry's other fields as JSON indented by
    two, in the order the protocol gives them."""
    got = served(mode) if got is None else got
    parts = [HEADER.format(mode=mode), _block("The opening text",
                                              got["opening"])]
    parts += [_described("Tool", entry, "name") for entry in got["tools"]]
    parts.append(_block("read_brief's answer", got["brief"]))
    for entry, text in got["prompts"]:
        parts.append(_described("Prompt", entry, "name") + _block(
            f"Prompt {entry['name']}: its text, each argument \"X\"", text))
    parts += [_described("Resource", entry, "uri")
              for entry in got["resources"]]
    parts += [_described("Resource template", entry, "uriTemplate")
              for entry in got["templates"]]
    parts += [_block(f"Resource {address}: its text", text)
              for address, text in got["guidance"]]
    return "".join(parts)[:-1]


def _definition(entry):
    return {"name": entry["name"], "description": entry.get("description", ""),
            "inputSchema": entry["inputSchema"]}


def measure(got):
    """A set's sizes: its tool count; the documented measure, the
    characters of json.dumps (Python's defaults) of every tool's name,
    description and input schema; each tool's description and its own
    entry; the opening text and the brief."""
    tools = got["tools"]
    return {"tool_count": len(tools),
            "tool_definitions_characters": len(json.dumps(
                [_definition(entry) for entry in tools])),
            "tools": {entry["name"]: {
                "description_characters": len(entry.get("description", "")),
                "definition_characters": len(json.dumps(_definition(entry)))}
                for entry in tools},
            "opening_text_characters": len(got["opening"]),
            "brief_characters": len(got["brief"])}


def snapshot():
    """The snapshot's files, by name, as the code serves them now."""
    files, sizes = {}, {"measured_on": MEASURED_ON, "counted": COUNTED}
    for mode in SETS:
        got = served(mode)
        files[f"{mode}.txt"] = render(mode, got)
        sizes[mode] = measure(got)
    files["sizes.json"] = json.dumps(sizes, indent=2, sort_keys=True) + "\n"
    return files


def committed(folder=SNAPSHOT):
    """The snapshot's files as committed, read as text, so that a
    checkout with Windows line ends reads the same; None for a file that
    is missing."""
    return {name: (folder / name).read_text(encoding="utf-8")
            if (folder / name).is_file() else None for name in FILES}


def differences(rendered, written, exact):
    """The first lines of a diff from a written text to a render, none
    when they agree: line by line when `exact`, otherwise word by word,
    white space set aside."""
    if exact:
        if rendered == written:
            return []
        old, new = written.split("\n"), rendered.split("\n")
    else:
        old, new = written.split(), rendered.split()
        if old == new:
            return []
    diff = difflib.unified_diff(old, new, "committed", "served", n=2,
                                lineterm="")
    return list(itertools.islice(diff, 40))


def compare(files, written, exact):
    """What differs between the snapshot's files and the ones written:
    every file exactly when `exact`; otherwise the texts with white space
    set aside and the tool counts alone of sizes.json."""
    found = []
    for name in FILES:
        if written.get(name) is None:
            found.append(f"docs/snapshot/{name} is missing.")
            continue
        if name == "sizes.json" and not exact:
            counts = [{mode: json.loads(text)[mode]["tool_count"]
                       for mode in SETS} for text in (written[name],
                                                      files[name])]
            if counts[0] != counts[1]:
                found.append(f"docs/snapshot/sizes.json counts {counts[0]} "
                             f"tools, and the code serves {counts[1]}.")
            continue
        lines = differences(files[name], written[name], exact)
        if lines:
            found += [f"docs/snapshot/{name} differs:"] + lines
    return found


def refusal(command, version):
    """Why `command` cannot run on this Python version, or None."""
    if command == "write" and tuple(version[:2]) != EXACT_ON:
        return (f"Not written: the snapshot is written on Python 3.13 "
                f"alone, and this is {version[0]}.{version[1]}; regenerate "
                f"it on Python 3.13.")
    return None


def installed(library):
    """The release of `library` installed here."""
    return importlib.metadata.version(library)


def locked(library):
    """The releases uv.lock gives `library`."""
    import tomllib
    with open(REPO / "uv.lock", "rb") as handle:
        packages = tomllib.load(handle)["package"]
    return {package["version"] for package in packages
            if package["name"] == library}


def library_refusal():
    """Why the snapshot cannot be written with the libraries installed,
    or None: the schemas come from mcp and pydantic, so their releases
    are the ones uv.lock gives."""
    for library in LIBRARIES:
        here, given = installed(library), locked(library)
        if here not in given:
            return (f"Not written: {library} {here} is installed, and "
                    f"uv.lock gives {library} {', '.join(sorted(given))}; "
                    f"install the lock's releases with `uv sync --frozen "
                    f"--extra dev --extra pdf-epub` (CONTRIBUTING.md, "
                    f"step 6).")
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python scripts/served_texts.py",
        description="Write or check docs/snapshot/: what Exegete sends "
                    "the assistant before a project is open, and the "
                    "brief.")
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="write the snapshot again")
    write.add_argument("--out", type=Path, default=SNAPSHOT,
                       help="another folder to write it in")
    commands.add_parser("check", help="compare it with what Exegete serves")
    args = parser.parse_args(argv)
    reason = refusal(args.command, sys.version_info)
    if reason is None and args.command == "write":
        reason = library_refusal()
    if reason:
        print(reason, file=sys.stderr)
        return 2
    pin_environment()
    print(f"Home folder for this run: {Path.home()}", file=sys.stderr)
    print(f"Temporary folder for this run: {tempfile.gettempdir()}",
          file=sys.stderr)
    import exegete
    source = Path(exegete.__file__).resolve()
    if (REPO / "src").resolve() not in source.parents:
        print(f"Stopped: exegete is imported from {source}, not from this "
              f"repository's src/; install the repository for development "
              f"(CONTRIBUTING.md, step 3).", file=sys.stderr)
        return 2
    logging.disable(logging.INFO)
    files = snapshot()
    if args.command == "write":
        args.out.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (args.out / name).write_text(text, encoding="utf-8",
                                         newline="\n")
        print(f"Wrote {', '.join(files)} in {args.out}.", file=sys.stderr)
        return 0
    found = compare(files, committed(),
                    tuple(sys.version_info[:2]) == EXACT_ON)
    print("\n".join(found) or "The snapshot is what Exegete serves.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
