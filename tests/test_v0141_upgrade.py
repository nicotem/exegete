# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: an upgrade through the old name, offline.

Slow; run by CI's `rename-upgrade` job on one computer, and skipped
elsewhere unless RENAME_TEST_WHEELHOUSE names a folder of wheels for
`mcp` and everything it needs, plus setuptools (that job fills one with
`pip download`). Everything is installed from that folder with
`--no-index`, so the real PyPI's qualcoder-mcp can never be picked up,
and at a test version no index holds.

The design's experiment, repeated with the real packages: a stand-in
for the published 0.14.0a0 (its file list is a fixture), upgraded by
the old name with pip, `uv pip`, `uv tool upgrade` and `uvx`. Each ends
with `qualcoder-mcp --version`, `python -m qualcoder_mcp.server
--version` and `exegete --version` answering, the old name's note on
standard error only. Then a copy of the source, installed with
`pip install -e .` before and after the rename.
"""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import rename_helpers as rh

pytestmark = pytest.mark.slow

REPO = rh.REPO
TEST_VERSION = "0.99.0a0"
OLD_FIXTURE = REPO / "tests" / "fixtures" / "qualcoder_mcp-0.14.0a0-wheel.json"
STARTED = f"exegete {TEST_VERSION} (started as qualcoder-mcp)"
BIN = "Scripts" if os.name == "nt" else "bin"
EXE = ".exe" if os.name == "nt" else ""


def _hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def write_old_release(folder: Path) -> Path:
    """A stand-in for the published qualcoder-mcp 0.14.0a0: the same
    file list, command and requirement; each module a stub."""
    spec = json.loads(OLD_FIXTURE.read_text(encoding="utf-8"))
    dist = f"qualcoder_mcp-{spec['version']}.dist-info"
    files = {name: b"# stand-in for the 0.14.0a0 release\n"
             for name in spec["modules"]}
    files["qualcoder_mcp/server.py"] = (
        b"def main():\n    print('qualcoder-mcp 0.14.0a0')\n\n"
        b"if __name__ == '__main__':\n    main()\n")
    meta = [f"Metadata-Version: 2.1", f"Name: {spec['name']}",
            f"Version: {spec['version']}"]
    meta += [f"Requires-Dist: {r}" for r in spec["requires_dist"]]
    files[f"{dist}/METADATA"] = ("\n".join(meta) + "\n").encode()
    files[f"{dist}/WHEEL"] = (b"Wheel-Version: 1.0\nGenerator: test\n"
                              b"Root-Is-Purelib: true\nTag: py3-none-any\n")
    files[f"{dist}/entry_points.txt"] = ("[console_scripts]\n" + "".join(
        f"{k} = {v}\n" for k, v in spec["console_scripts"].items())).encode()
    files[f"{dist}/top_level.txt"] = b"qualcoder_mcp\n"
    record = [f"{n},{_hash(d)},{len(d)}" for n, d in files.items()]
    record.append(f"{dist}/RECORD,,")
    files[f"{dist}/RECORD"] = ("\n".join(record) + "\n").encode()
    target = folder / f"qualcoder_mcp-{spec['version']}-py3-none-any.whl"
    with zipfile.ZipFile(target, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return target


@pytest.fixture(scope="module")
def houses(tmp_path_factory):
    """{'old': deps + the 0.14.0a0 stand-in,
        'new': that + both new wheels at TEST_VERSION}."""
    source = os.environ.get(rh.WHEELHOUSE)
    if not source or not Path(source).is_dir():
        rh.skip_or_fail(f"{rh.WHEELHOUSE} does not name a folder of wheels")
    rh.need_setuptools()
    if shutil.which("uv") is None:
        rh.skip_or_fail("uv is needed for the uv cases")
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
    return {"old": old, "new": new, "tmp": tmp}


def _env(tmp: Path) -> dict:
    """No index, no configuration and no home of the developer's."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PIP_", "UV_", "QUALCODER", "EXEGETE",
                                "VIRTUAL_ENV", "PYTHON"))}
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    env.update({"HOME": str(home), "USERPROFILE": str(home),
                "UV_CACHE_DIR": str(tmp / "uv-cache"),
                "UV_TOOL_DIR": str(tmp / "uv-tools"),
                "UV_TOOL_BIN_DIR": str(tmp / "uv-bin"),
                "UV_PYTHON_DOWNLOADS": "never", "UV_NO_CONFIG": "1",
                "PIP_CONFIG_FILE": os.devnull,
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def run(args, env, check=True):
    proc = subprocess.run([str(a) for a in args], capture_output=True,
                          text=True, encoding="utf-8", env=env,
                          timeout=240)
    if check:
        assert proc.returncode == 0, (args, proc.stdout[-2000:],
                                      proc.stderr[-2000:])
    return proc


def offline(house):
    return ["--no-index", "--find-links", str(house)]


def assert_answers(env, old_cmd, python, new_cmd):
    """The three ways in, each answering with the new version."""
    for args in ([old_cmd, "--version"],
                 [python, "-m", "qualcoder_mcp.server", "--version"]):
        proc = run(args, env)
        assert proc.stdout.strip() == STARTED, args
        assert proc.stderr == "", args          # the note only at a start
    proc = run([new_cmd, "--version"], env)
    assert proc.stdout.split()[-1] == TEST_VERSION
    assert "started as" not in proc.stdout
    proc = run([python, "-c", "import exegete; print(exegete.__version__)"],
               env)
    assert proc.stdout.strip() == TEST_VERSION
    # only the two ways of starting survive, not the inner modules
    proc = run([python, "-c", "import qualcoder_mcp.database"], env,
               check=False)
    assert proc.returncode != 0


def _venv(tmp: Path, name: str, env) -> Path:
    folder = tmp / name
    run([sys.executable, "-m", "venv", folder], env)
    return folder


def _installed_old(env, folder):
    proc = run([folder / BIN / f"qualcoder-mcp{EXE}"], env)
    assert proc.stdout.strip() == "qualcoder-mcp 0.14.0a0"


class TestUpgradingByTheOldName:

    def test_pip(self, houses, tmp_path):
        env = _env(tmp_path)
        venv = _venv(tmp_path, "pip-env", env)
        python = venv / BIN / f"python{EXE}"
        run([python, "-m", "pip", "install", *offline(houses["old"]),
             "qualcoder-mcp"], env)
        _installed_old(env, venv)
        run([python, "-m", "pip", "install", "--upgrade",
             *offline(houses["new"]), "qualcoder-mcp"], env)
        assert_answers(env, venv / BIN / f"qualcoder-mcp{EXE}", python,
                       venv / BIN / f"exegete{EXE}")

    def test_uv_pip(self, houses, tmp_path):
        env = _env(tmp_path)
        venv = tmp_path / "uv-env"
        run(["uv", "venv", "--python", sys.executable, venv], env)
        python = venv / BIN / f"python{EXE}"
        run(["uv", "pip", "install", "--python", python,
             *offline(houses["old"]), "qualcoder-mcp"], env)
        _installed_old(env, venv)
        run(["uv", "pip", "install", "--python", python, "--upgrade",
             *offline(houses["new"]), "qualcoder-mcp"], env)
        assert_answers(env, venv / BIN / f"qualcoder-mcp{EXE}", python,
                       venv / BIN / f"exegete{EXE}")

    def test_uv_tool_upgrade(self, houses, tmp_path):
        env = _env(tmp_path)
        run(["uv", "tool", "install", "--python", sys.executable,
             *offline(houses["old"]), "qualcoder-mcp"], env)
        command = Path(env["UV_TOOL_BIN_DIR"]) / f"qualcoder-mcp{EXE}"
        assert run([command], env).stdout.strip() == "qualcoder-mcp 0.14.0a0"
        run(["uv", "tool", "upgrade", *offline(houses["new"]),
             "qualcoder-mcp"], env)
        tool = Path(env["UV_TOOL_DIR"]) / "qualcoder-mcp"
        assert_answers(env, command, tool / BIN / f"python{EXE}",
                       tool / BIN / f"exegete{EXE}")
        # uv puts only the named package's commands on the path
        assert not (Path(env["UV_TOOL_BIN_DIR"]) / f"exegete{EXE}").exists()

    def test_uvx(self, houses, tmp_path):
        env = _env(tmp_path)
        proc = run(["uvx", "--python", sys.executable,
                    *offline(houses["new"]), "--offline", "qualcoder-mcp",
                    "--version"], env)
        assert proc.stdout.strip() == STARTED
        proc = run(["uvx", "--python", sys.executable,
                    *offline(houses["new"]), "--offline", "exegete",
                    "--version"], env)
        assert proc.stdout.split()[-1] == TEST_VERSION


def test_the_version_is_exegetes_beside_the_old_names(houses, tmp_path):
    """With the old name's package installed beside it at another
    version, __version__ still reads exegete's own."""
    house = tmp_path / "house"
    shutil.copytree(houses["old"], house)
    built = rh.build_both(tmp_path / "build", TEST_VERSION, "0.99.1a0",
                          TEST_VERSION)
    for path in built["exegete"] + built["old"]:
        if path.suffix == ".whl":
            shutil.copy(path, house)
    env = _env(tmp_path)
    venv = _venv(tmp_path, "env", env)
    python = venv / BIN / f"python{EXE}"
    run([python, "-m", "pip", "install", *offline(house),
         "qualcoder-mcp==0.99.1a0"], env)
    proc = run([python, "-c", "import exegete; print(exegete.__version__)"],
               env)
    assert proc.stdout.strip() == TEST_VERSION
    proc = run([venv / BIN / f"qualcoder-mcp{EXE}", "--version"], env)
    assert proc.stdout.strip() == STARTED


def _old_clone(tree: Path):
    """Turn a copy of this tree back into a 0.14.0 layout: the package
    under its old name, and pyproject's old name and command."""
    shutil.rmtree(tree / "src" / "qualcoder_mcp")
    (tree / "src" / "exegete").rename(tree / "src" / "qualcoder_mcp")
    path = tree / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    for old, new in (('name = "exegete"', 'name = "qualcoder-mcp"'),
                     ('exegete = "exegete.server:main"',
                      'qualcoder-mcp = "qualcoder_mcp.server:main"'),
                     ('exclude = ["qualcoder_mcp", "qualcoder_mcp.*"]', "")):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def _pull(tree: Path):
    """What `git pull` does to that copy: the renamed tree arrives."""
    shutil.rmtree(tree / "src")
    shutil.copytree(REPO / "src", tree / "src",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                  "*.egg-info"))
    shutil.copyfile(REPO / "pyproject.toml", tree / "pyproject.toml")


class TestACopyOfTheSource:
    """INSTALL's git route: `pip install -e .` of a clone, whose host
    entry runs `python -m qualcoder_mcp.server` or the old command. The
    stand-in is left out of the exegete wheel, but an editable install
    puts the whole src folder on the path (setuptools' default mode), so
    it still answers there."""

    def test_an_update_without_reinstalling_then_the_usual_reinstall(
            self, houses, tmp_path):
        env = _env(tmp_path)
        tree = rh.copy_tree(tmp_path / "clone")
        _old_clone(tree)
        venv = _venv(tmp_path, "venv", env)
        python = venv / BIN / f"python{EXE}"
        old_cmd = venv / BIN / f"qualcoder-mcp{EXE}"
        run([python, "-m", "pip", "install", *offline(houses["old"]),
             "-e", tree], env)
        assert run([python, "-c", "import qualcoder_mcp.database"], env)

        _pull(tree)                      # no reinstall, as after git pull
        for args in ([old_cmd, "--version"],
                     [python, "-m", "qualcoder_mcp.server", "--version"]):
            proc = run(args, env)
            assert proc.stdout.strip().endswith(
                "(started as qualcoder-mcp)"), args
            assert proc.stderr == ""

        # INSTALL's Path A: pip install -e . again after the pull
        run([python, "-m", "pip", "install", *offline(houses["old"]),
             "-e", tree], env)
        version = run([python, "-c",
                       "import exegete; print(exegete.__version__)"],
                      env).stdout.strip()
        assert version != "0.0.0+unknown"
        started = f"exegete {version} (started as qualcoder-mcp)"
        for args in ([old_cmd, "--version"],
                     [python, "-m", "qualcoder_mcp.server", "--version"]):
            assert run(args, env).stdout.strip() == started, args
        assert run([venv / BIN / f"exegete{EXE}", "--version"],
                   env).stdout.split()[-1] == version

    def test_a_fresh_editable_install(self, houses, tmp_path):
        env = _env(tmp_path)
        tree = rh.copy_tree(tmp_path / "clone")
        venv = _venv(tmp_path, "venv", env)
        python = venv / BIN / f"python{EXE}"
        run([python, "-m", "pip", "install", *offline(houses["old"]),
             "-e", tree], env)
        proc = run([python, "-m", "qualcoder_mcp.server", "--version"], env)
        assert proc.stdout.strip().endswith("(started as qualcoder-mcp)")
        assert not (venv / BIN / f"qualcoder-mcp{EXE}").exists()
