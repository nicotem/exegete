# SPDX-License-Identifier: LGPL-3.0-or-later
"""Compare what two releases of Exegete offer an assistant and a researcher.

Release preparation writes "Upgrading from <the last release>" from a
mechanical comparison rather than from memory (owner's ruling 85, item 5).
Two steps, each run in the environment of the tree it describes:

    python scripts/compare_release_surface.py dump OUT.json
    python scripts/compare_release_surface.py diff OLD.json NEW.json

`dump` records, from the installed `exegete` and the tree around it:
every tool's name, title, annotations, description (length and digest),
arguments (name, type, default, required) and declared answer schema;
the members of each tool set and their measured size (the `tools/list`
payload, measured as docs/snapshot/sizes.json gives it); the help topics;
the environment variables the code names; the extension's settings;
the keys the code puts in its answers and the values it gives under
`reason`, `status` and `kind`; and the length of the opening text.
`diff` prints what was removed, added and changed between two dumps.
Run every step with HOME and USERPROFILE pinned to a scratch folder.
"""
import ast
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

CODE_KEYS = ("reason", "status", "kind")
ENV_RE = re.compile(r"^(EXEGETE|QUALCODER_MCP)_[A-Z0-9_]+$")


def _arg(schema, required):
    kind = schema.get("type") or [a.get("type") for a in schema.get("anyOf", [])]
    out = {"type": kind, "required": required}
    if "default" in schema:
        out["default"] = schema["default"]
    if "enum" in schema:
        out["enum"] = schema["enum"]
    return out


def _tools(server):
    tools = asyncio.run(server.mcp.list_tools())
    payload = [{"name": t.name, "description": t.description or "",
                "inputSchema": t.inputSchema} for t in tools]
    out = {}
    for t in tools:
        schema = t.inputSchema or {}
        req = set(schema.get("required", []))
        desc = t.description or ""
        out[t.name] = {
            "title": t.title,
            "annotations": t.annotations.model_dump(exclude_none=True)
            if t.annotations else None,
            "description_chars": len(desc),
            "description_sha": hashlib.sha256(desc.encode()).hexdigest()[:12],
            "arguments": {k: _arg(v, k in req)
                          for k, v in schema.get("properties", {}).items()},
            "answer_schema": getattr(t, "outputSchema", None),
        }
    return out, len(json.dumps(payload))


def _source_facts(src):
    keys, codes, envs = set(), {k: set() for k in CODE_KEYS}, set()
    for path in sorted(Path(src).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if ENV_RE.match(node.value):
                    envs.add(node.value)
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
                    if (k.value in CODE_KEYS and isinstance(v, ast.Constant)
                            and isinstance(v.value, str)):
                        codes[k.value].add(v.value)
    return sorted(keys), {k: sorted(v) for k, v in codes.items()}, sorted(envs)


def _help_topics(server, names):
    found = {}
    for topic in sorted(set(names) | {"grounding_rules", "brief",
                                      "coding_style_guidance"}):
        try:
            answer = json.loads(server.explain_ai_coding_tools(topic))
        except Exception as e:  # recorded, not hidden
            answer = {"raised": type(e).__name__}
        if isinstance(answer, dict) and "available_tools" not in answer \
                and "error" not in answer and "raised" not in answer:
            found[topic] = sorted(answer)
    overview = json.loads(server.explain_ai_coding_tools("__no_such_topic__"))
    return found, overview.get("available_tools")


def dump(out_path):
    from exegete import server
    import exegete
    root = Path(exegete.__file__).resolve().parents[2]
    full, full_size = _tools(server)
    removed = server._apply_toolset("core")
    try:
        core, core_size = _tools(server)
    finally:
        for name, tool in removed.items():
            server.mcp._tool_manager._tools[name] = tool
    keys, codes, envs = _source_facts(Path(exegete.__file__).parent)
    topics, listed = _help_topics(server, full)
    manifest = json.loads((root / "packaging/desktop-extension/"
                           "manifest.in.json").read_text(encoding="utf-8"))
    data = {
        "version": __import__("importlib.metadata").metadata.version("exegete"),
        "python": sys.version.split()[0],
        "tools": full,
        "toolsets": {"full": sorted(full), "core": sorted(core)},
        "sizes": {"full": full_size, "core": core_size,
                  "opening_text": len(server.mcp.instructions or "")},
        "help_topics": topics, "help_topics_listed": listed,
        "environment_variables": envs,
        "extension_settings": {k: [v.get("type"), v.get("title"),
                                   v.get("default")]
                               for k, v in manifest["user_config"].items()},
        "extension_env": manifest["server"]["mcp_config"].get("env", {}),
        "answer_keys": keys, "answer_codes": codes,
    }
    Path(out_path).write_text(json.dumps(data, indent=1, sort_keys=True,
                                         default=str), encoding="utf-8")
    print(f"{data['version']} on {data['python']}: {len(full)} tools, "
          f"core {len(core)}, full {full_size}, core {core_size}")


def _sets(label, old, new, out):
    old, new = set(old), set(new)
    if old - new:
        out.append(f"{label} removed: {', '.join(sorted(old - new))}")
    if new - old:
        out.append(f"{label} added: {', '.join(sorted(new - old))}")


def diff(old_path, new_path):
    a = json.loads(Path(old_path).read_text(encoding="utf-8"))
    b = json.loads(Path(new_path).read_text(encoding="utf-8"))
    out = [f"# {a['version']} ({a['python']}) -> {b['version']} ({b['python']})"]
    for k in ("full", "core", "opening_text"):
        out.append(f"size {k}: {a['sizes'][k]} -> {b['sizes'][k]} "
                   f"({b['sizes'][k] - a['sizes'][k]:+d})")
    for ts in ("full", "core"):
        out.append(f"tool set {ts}: {len(a['toolsets'][ts])} -> "
                   f"{len(b['toolsets'][ts])}")
        _sets(f"tool set {ts}", a["toolsets"][ts], b["toolsets"][ts], out)
    for name in sorted(set(a["tools"]) & set(b["tools"])):
        ta, tb = a["tools"][name], b["tools"][name]
        if ta["description_sha"] != tb["description_sha"]:
            out.append(f"tool {name}: description {ta['description_chars']} -> "
                       f"{tb['description_chars']} "
                       f"({tb['description_chars'] - ta['description_chars']:+d})")
        for field in ("title", "annotations", "answer_schema"):
            if ta[field] != tb[field]:
                out.append(f"tool {name}: {field} {ta[field]} -> {tb[field]}")
        aa, ab = ta["arguments"], tb["arguments"]
        _sets(f"tool {name}: argument", aa, ab, out)
        for arg in sorted(set(aa) & set(ab)):
            if aa[arg] != ab[arg]:
                out.append(f"tool {name}: argument {arg} {aa[arg]} -> {ab[arg]}")
    _sets("help topic", a["help_topics"], b["help_topics"], out)
    _sets("help topic listed", a["help_topics_listed"] or [],
          b["help_topics_listed"] or [], out)
    _sets("environment variable", a["environment_variables"],
          b["environment_variables"], out)
    for k in sorted(set(a["extension_settings"]) | set(b["extension_settings"])):
        if a["extension_settings"].get(k) != b["extension_settings"].get(k):
            out.append(f"extension setting {k}: {a['extension_settings'].get(k)}"
                       f" -> {b['extension_settings'].get(k)}")
    for k in sorted(set(a["extension_env"]) | set(b["extension_env"])):
        if a["extension_env"].get(k) != b["extension_env"].get(k):
            out.append(f"extension env {k}: {a['extension_env'].get(k)} -> "
                       f"{b['extension_env'].get(k)}")
    _sets("answer key", a["answer_keys"], b["answer_keys"], out)
    for k in sorted(set(a["answer_codes"]) | set(b["answer_codes"])):
        _sets(f"answer {k}", a["answer_codes"].get(k, []),
              b["answer_codes"].get(k, []), out)
    print("\n".join(out))


if __name__ == "__main__":
    if sys.argv[1:2] == ["dump"] and len(sys.argv) == 3:
        dump(sys.argv[2])
    elif sys.argv[1:2] == ["diff"] and len(sys.argv) == 4:
        diff(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
