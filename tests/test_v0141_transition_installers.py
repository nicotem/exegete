# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the transition check's steps, followed with the real installers.

Slow, like test_v0141_upgrade.py: run when RENAME_TEST_WHEELHOUSE names a
folder of wheels (`mcp` and what it needs, plus setuptools; for pipx,
pipx and what it needs as well, else a pipx on the PATH is used), and
skipped elsewhere. CI's rename job runs it on Linux. Everything is
installed offline from that folder, at a test version no index holds.

For an install made with uv tool and one made with pipx, each first at
the published 0.14.0a0 (a stand-in with its file list) and then upgraded
by the old name to this tree's two packages, as INSTALL says: the old
command runs the check, and its printed steps are followed in order,
exactly as printed (each command through the shell, each entry's lines
pasted into Claude Desktop's file in a scratch home). After every step
the host's entry starts a command that answers; at the end it starts a
server that answers MCP's `initialize` as Exegete, and the check finds
nothing left. And once more for pipx with `--include-deps`, which links
exegete's command from the old package's own environment, and for uv tool
with `--with-executables-from exegete`, which does the same and records
the command as the old package's (with two small wheels made here, so
that it needs uv alone).
"""

import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import rename_helpers as rh
from exegete import transition
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
    """The folder of a pipx command: one installed from the wheelhouse
    into an environment of its own when the wheelhouse holds pipx (CI's
    does, so a runner's own pipx, whatever its version, is not used), or
    else the one on the PATH."""
    if not list(source.glob("pipx-*.whl")):
        found = shutil.which("pipx")
        return Path(found).parent if found else None
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


def follow_the_check(houses, env, install, remove, linked=False):
    """`linked`: the exegete command is already there, linked from the
    old package's own environment."""
    home = Path(env["HOME"])
    old = home / ".local" / "bin" / "qualcoder-mcp"
    assert "(started as qualcoder-mcp)" in answers({"command": str(old)},
                                                   env)
    # as INSTALL says: these tools put only the named package's commands
    # on the PATH, unless asked for its dependencies' commands too
    exegete = home / ".local" / "bin" / "exegete"
    assert exegete.exists() == linked
    if linked:
        assert Path(os.path.realpath(exegete)).parent == \
            Path(os.path.realpath(old)).parent
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

    @staticmethod
    def _pipx_env(houses, tmp_path):
        if houses["pipx"] is None:
            rh.skip_or_fail("pipx is needed: its wheels in the wheelhouse, "
                            "or on the PATH")
        env = _env(tmp_path, [houses["pipx"]])
        # pip, as pipx has always used; recent pipx would use uv when it
        # finds a new enough one, which reads PIP_FIND_LINKS not at all
        env["PIPX_DEFAULT_BACKEND"] = "pip"
        return env

    def test_pipx(self, houses, tmp_path):
        env = self._pipx_env(houses, tmp_path)
        run(["pipx", "install", "qualcoder-mcp"],
            dict(env, PIP_FIND_LINKS=str(houses["old"])))
        run(["pipx", "upgrade", "qualcoder-mcp"],
            dict(env, PIP_FIND_LINKS=str(houses["new"])))
        follow_the_check(houses, env, ["pipx", "install", "exegete"],
                         ["pipx", "uninstall", "qualcoder-mcp"])

    def test_pipx_with_its_dependencies_commands(self, houses, tmp_path):
        # pipx will not replace a command linked from another environment
        # without --force, and removing the old package would take it
        env = self._pipx_env(houses, tmp_path)
        run(["pipx", "install", "--include-deps", "qualcoder-mcp"],
            dict(env, PIP_FIND_LINKS=str(houses["new"])))
        follow_the_check(houses, env,
                         ["pipx", "install", "--force", "exegete"],
                         ["pipx", "uninstall", "qualcoder-mcp"],
                         linked=True)


def small_wheel(folder: Path, dist: str, version: str, command: str,
                requires=()) -> Path:
    """A wheel holding one module whose command prints the package's name
    and version, made here: no index and no build are needed."""
    module = dist.replace("-", "_") + "_small"
    info = f"{dist.replace('-', '_')}-{version}.dist-info"
    files = {
        f"{module}.py": ("import sys\n\ndef main():\n"
                         f"    print('{dist} {version}', sys.argv[1:])\n"),
        f"{info}/METADATA": (f"Metadata-Version: 2.1\nName: {dist}\n"
                             f"Version: {version}\n" +
                             "".join(f"Requires-Dist: {r}\n"
                                     for r in requires)),
        f"{info}/WHEEL": ("Wheel-Version: 1.0\nGenerator: test\n"
                          "Root-Is-Purelib: true\nTag: py3-none-any\n"),
        f"{info}/entry_points.txt": (f"[console_scripts]\n"
                                     f"{command} = {module}:main\n"),
    }
    record = []
    for name, text in files.items():
        data = text.encode("utf-8")
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
        record.append(f"{name},sha256={digest},{len(data)}")
    files[f"{info}/RECORD"] = "\n".join(record + [f"{info}/RECORD,,"]) + "\n"
    path = folder / f"{dist.replace('-', '_')}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as wheel:
        for name, text in files.items():
            wheel.writestr(name, text)
    return path


def test_uv_tool_with_executables_from_exegete(tmp_path):
    # uv records exegete's command in the old tool's receipt, and its
    # uninstall removes it even after Exegete's own install relinked it,
    # so the step that removes the old package installs the command
    # once more; after every step the host's entry starts a command
    if shutil.which("uv") is None:
        rh.skip_or_fail("uv is needed for the uv tool case")
    house = tmp_path / "house"
    house.mkdir()
    small_wheel(house, "exegete", TEST_VERSION, "exegete")
    small_wheel(house, "qualcoder-mcp", TEST_VERSION, "qualcoder-mcp",
                ["exegete"])
    env = dict(_env(tmp_path), UV_FIND_LINKS=str(house))
    run(["uv", "tool", "install", "--no-index", "qualcoder-mcp",
         "--with-executables-from", "exegete"], env)
    home = Path(env["HOME"])
    folder = home / ".local" / "bin"
    assert Path(os.path.realpath(folder / "exegete")).parent == \
        Path(os.path.realpath(folder / "qualcoder-mcp")).parent
    config = home / "Library" / "Application Support" / "Claude" / \
        "claude_desktop_config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"qualcoder": {
        "command": str(folder / "qualcoder-mcp")}}}), encoding="utf-8")

    def check():
        out = io.StringIO()
        code = transition.run(
            out=out, home=home, prefix=home / "no-env",
            which=lambda name: shutil.which(name, path=env["PATH"]),
            listing=lambda: [])
        return code, out.getvalue()

    code, out = check()
    install = "uv tool install --force exegete"
    remove = "uv tool uninstall qualcoder-mcp"
    assert code == 1 and pasted(out)[0] == install, out
    assert pasted(out)[-2:] == [remove, install], out
    done = follow(out, config, env)
    assert done == [install, "entry", remove, install]
    entry = json.loads(config.read_text(encoding="utf-8"))[
        "mcpServers"]["qualcoder"]
    assert entry == {"command": str(folder / "exegete"), "args": []}
    assert f"exegete {TEST_VERSION}" in answers(entry, env)
    code, out = check()
    assert code == 0, out
