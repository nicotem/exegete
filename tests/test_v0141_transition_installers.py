# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the transition check's steps, followed with the real installers.

Slow, like test_v0141_upgrade.py: run when RENAME_TEST_WHEELHOUSE names a
folder of wheels (`mcp` and what it needs, plus setuptools; for pipx,
pipx and what it needs as well, unless a pipx is on the PATH), and
skipped elsewhere. Everything is installed offline from that folder, at
a test version no index holds.

For an install made with uv tool and one made with pipx, each first at
the published 0.14.0a0 (a stand-in with its file list) and then upgraded
by the old name to this tree's two packages, as INSTALL says: the old
command runs the check, and its printed steps are followed in order,
exactly as printed (each command through the shell, each entry's lines
pasted into Claude Desktop's file in a scratch home). After every step
the host's entry starts a command that answers; at the end it starts a
server that answers MCP's `initialize` as Exegete, and the check finds
nothing left.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import rename_helpers as rh
from test_v0141_transition import items, pasted
from test_v0141_upgrade import TEST_VERSION, write_old_release

pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(os.name == "nt", reason="the steps are "
                                 "run through sh; CI runs them on Linux")]


@pytest.fixture(scope="module")
def houses(tmp_path_factory):
    """{'old': deps + the 0.14.0a0 stand-in, 'new': that + both new
    wheels at TEST_VERSION, 'pipx': a folder holding a pipx command}."""
    source = os.environ.get(rh.WHEELHOUSE)
    if not source or not Path(source).is_dir():
        rh.skip_or_fail(f"{rh.WHEELHOUSE} does not name a folder of wheels")
    rh.need_setuptools()
    if shutil.which("uv") is None:
        rh.skip_or_fail("uv is needed for the uv tool case")
    tmp = tmp_path_factory.mktemp("houses")
    old = tmp / "old"
    shutil.copytree(source, old)
    write_old_release(old)
    new = tmp / "new"
    shutil.copytree(old, new)
    built = rh.build_both(tmp / "build", TEST_VERSION)
    for path in built["exegete"] + built["old"]:
        if path.suffix == ".whl":
            shutil.copy(path, new)
    return {"old": old, "new": new, "tmp": tmp,
            "pipx": _pipx(tmp, Path(source))}


def _pipx(tmp: Path, source: Path):
    """The folder of a pipx command: the one on the PATH, or one
    installed from the wheelhouse into an environment of its own."""
    found = shutil.which("pipx")
    if found:
        return Path(found).parent
    if not list(source.glob("pipx-*.whl")):
        return None
    env = tmp / "pipx-env"
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True,
                   timeout=120)
    subprocess.run([str(env / "bin" / "python"), "-m", "pip", "install",
                    "--no-index", "--find-links", str(source), "pipx"],
                   check=True, capture_output=True, timeout=180)
    return env / "bin"


def _env(tmp: Path, extra_path=()) -> dict:
    """A scratch home, the installers' own defaults under it, no index."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PIP_", "UV_", "PIPX_", "XDG_",
                                "QUALCODER", "EXEGETE", "VIRTUAL_ENV",
                                "PYTHON"))}
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    env.update({"HOME": str(home), "USERPROFILE": str(home),
                "TMPDIR": str(tmp), "UV_CACHE_DIR": str(tmp / "uv-cache"),
                "UV_PYTHON": sys.executable,
                "UV_PYTHON_DOWNLOADS": "never", "UV_NO_CONFIG": "1",
                "UV_OFFLINE": "1", "PIP_CONFIG_FILE": os.devnull,
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_INDEX": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    folders = [str(home / ".local" / "bin"), *map(str, extra_path),
               str(Path(shutil.which("uv")).parent)]
    env["PATH"] = os.pathsep.join(folders + [env.get("PATH", "")])
    return env


def run(args, env, check=True, **kwargs):
    proc = subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", env=env,
                          timeout=240, **kwargs)
    if check:
        assert proc.returncode == 0, (args, proc.stdout[-3000:],
                                      proc.stderr[-3000:])
    return proc


def answers(entry: dict, env) -> str:
    """What the host's entry starts, asked for its version."""
    proc = run([entry["command"], *entry.get("args", []), "--version"], env)
    return proc.stdout.strip()


def starts_a_server(entry: dict, env) -> dict:
    """The entry's server, sent MCP's initialize: its answer's result."""
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18",
                          "capabilities": {},
                          "clientInfo": {"name": "test", "version": "0"}}}
    proc = run([entry["command"], *entry.get("args", [])], env,
               input=json.dumps(request) + "\n")
    for line in proc.stdout.splitlines():
        message = json.loads(line)
        if message.get("id") == 1:
            return message["result"]
    raise AssertionError(proc.stdout + proc.stderr)


def follow(out: str, config: Path, env) -> list:
    """The report's steps in order, exactly as printed: each command run
    through sh, each entry's lines pasted into the host's file. After
    each step the host's entry must still start a command that answers."""
    done = []
    for what, lines in items(out):
        commands = [line[7:] for line in lines
                    if line.startswith("       ") and line[7:8] != " "]
        entry_lines = [c for c in commands if c.startswith('"')]
        if entry_lines:
            data = json.loads(config.read_text(encoding="utf-8"))
            data["mcpServers"]["qualcoder"].update(
                json.loads("{" + " ".join(entry_lines) + "}"))
            config.write_text(json.dumps(data), encoding="utf-8")
            done.append("entry")
        for command in commands:
            if not command.startswith('"'):
                run(["/bin/sh", "-c", command], env)
                done.append(command)
        entry = json.loads(config.read_text(encoding="utf-8"))[
            "mcpServers"]["qualcoder"]
        assert TEST_VERSION in answers(entry, env), (what, done)
    return done


def follow_the_check(houses, env, install, remove):
    home = Path(env["HOME"])
    old = home / ".local" / "bin" / "qualcoder-mcp"
    assert "(started as qualcoder-mcp)" in answers({"command": str(old)},
                                                   env)
    # as INSTALL says: these tools put only the named package's commands
    # on the PATH
    assert not (home / ".local" / "bin" / "exegete").exists()
    config = home / "Library" / "Application Support" / "Claude" / \
        "claude_desktop_config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"qualcoder": {
        "command": str(old)}}}), encoding="utf-8")
    first = run([old, "--check-transition"], env, check=False)
    assert first.returncode == 1, first.stdout + first.stderr
    printed = pasted(first.stdout)
    assert printed[0] == " ".join(install), first.stdout
    assert printed[-1] == " ".join(remove), first.stdout
    steps = dict(env, UV_FIND_LINKS=str(houses["new"]),
                 PIP_FIND_LINKS=str(houses["new"]))
    done = follow(first.stdout, config, steps)
    assert done == [" ".join(install), "entry", " ".join(remove)]
    assert not old.exists()
    entry = json.loads(config.read_text(encoding="utf-8"))[
        "mcpServers"]["qualcoder"]
    assert entry == {"command": str(home / ".local" / "bin" / "exegete"),
                     "args": []}
    assert starts_a_server(entry, env)["serverInfo"]["name"] == "Exegete"
    last = run([entry["command"], "--check-transition"], env, check=False)
    assert last.returncode == 0, last.stdout


class TestFollowingTheSteps:

    def test_uv_tool(self, houses, tmp_path):
        env = _env(tmp_path)
        run(["uv", "tool", "install", "--no-index", "--find-links",
             houses["old"], "qualcoder-mcp"], env)
        run(["uv", "tool", "upgrade", "--no-index", "--find-links",
             houses["new"], "qualcoder-mcp"], env)
        follow_the_check(houses, env, ["uv", "tool", "install", "exegete"],
                         ["uv", "tool", "uninstall", "qualcoder-mcp"])

    def test_pipx(self, houses, tmp_path):
        if houses["pipx"] is None:
            rh.skip_or_fail("pipx is needed: on the PATH, or its wheels in "
                            "the wheelhouse")
        env = _env(tmp_path, [houses["pipx"]])
        # pip, as pipx has always used; recent pipx would use uv when it
        # finds a new enough one, which reads PIP_FIND_LINKS not at all
        env["PIPX_DEFAULT_BACKEND"] = "pip"
        run(["pipx", "install", "qualcoder-mcp"],
            dict(env, PIP_FIND_LINKS=str(houses["old"])))
        run(["pipx", "upgrade", "qualcoder-mcp"],
            dict(env, PIP_FIND_LINKS=str(houses["new"])))
        follow_the_check(houses, env, ["pipx", "install", "exegete"],
                         ["pipx", "uninstall", "qualcoder-mcp"])
