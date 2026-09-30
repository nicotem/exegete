# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: starting the server by its old name.

`qualcoder-mcp` (the command) and `python -m qualcoder_mcp.server` run
the two-file stand-in `qualcoder_mcp`, which hands over to
`exegete.server:main` with `started_as="qualcoder-mcp"`. The server
then says, in one line on standard error, that the command is now
`exegete`; `--version` answers `exegete <version> (started as
qualcoder-mcp)`; standard output stays the protocol's alone.

This is the only test module that imports `qualcoder_mcp`: the hygiene
test at the end keeps it so, because a leftover `import qualcoder_mcp`
elsewhere could quietly load an old copy of the package from an old
editable install and pass for the wrong reason.
"""

import ast
import asyncio
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete                                    # noqa: E402
import exegete.server as server                   # noqa: E402
import qualcoder_mcp                              # noqa: E402
import qualcoder_mcp.server as stand_in           # noqa: E402

NOTE = ("qualcoder-mcp is now called Exegete; the command is `exegete`, "
        "and `exegete --check-transition` lists what the change left "
        "behind")


def _env(home):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QUALCODER", "EXEGETE"))}
    env.update({"PYTHONPATH": str(REPO / "src"), "HOME": str(home),
                "USERPROFILE": str(home), "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def test_both_packages_are_this_trees():
    """Never an old copy from an editable install elsewhere."""
    for module in (exegete, qualcoder_mcp, stand_in):
        assert Path(module.__file__).resolve().is_relative_to(REPO / "src")


class TestThePromise:
    """exegete.server:main, with its `started_as` keyword, is what the
    stand-in calls, and the old name's last release will call it for
    good: never removed, never renamed."""

    def test_main_takes_started_as_by_keyword(self):
        parameters = inspect.signature(server.main).parameters
        assert list(parameters) == ["argv", "started_as"]
        assert parameters["started_as"].kind is \
            inspect.Parameter.KEYWORD_ONLY
        assert parameters["started_as"].default is None

    def test_the_stand_in_exposes_main(self):
        assert callable(stand_in.main)

    def test_nothing_else_of_the_old_package_survives(self):
        assert not hasattr(qualcoder_mcp, "__version__")
        folder = REPO / "src" / "qualcoder_mcp"
        assert sorted(p.name for p in folder.glob("*.py")) == \
            ["__init__.py", "server.py"]


class TestVersion:

    def test_in_process(self, capsys):
        with pytest.raises(SystemExit) as exc:
            stand_in.main(["--version"])
        assert exc.value.code == 0
        out = capsys.readouterr()
        assert out.out.strip() == \
            f"exegete {exegete.__version__} (started as qualcoder-mcp)"
        assert out.err == ""

    def test_python_dash_m(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "qualcoder_mcp.server",
             "--version"], capture_output=True, text=True,
            encoding="utf-8", env=_env(home), timeout=120)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == \
            f"exegete {exegete.__version__} (started as qualcoder-mcp)"
        assert proc.stderr == ""
        assert list(home.iterdir()) == []

    def test_the_new_name_says_nothing_of_the_old(self, capsys):
        with pytest.raises(SystemExit):
            server.main(["--version"])
        assert "started as" not in capsys.readouterr().out


class TestTheNote:

    @pytest.fixture
    def stub_run(self, monkeypatch):
        calls = []
        monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
        monkeypatch.delenv("QUALCODER_PROJECT_PATH", raising=False)
        monkeypatch.delenv("QUALCODER_MCP_TOOLSET", raising=False)
        return calls

    def test_started_by_the_old_name_it_says_so_on_stderr(
            self, capsys, stub_run, caplog):
        caplog.set_level("INFO")
        stand_in.main([])
        out = capsys.readouterr()
        assert out.out == ""
        assert [r.getMessage() for r in caplog.records].count(NOTE) == 1
        assert stub_run == [{"transport": "stdio"}]

    def test_started_by_the_new_name_it_does_not(self, stub_run, caplog):
        caplog.set_level("INFO")
        server.main([])
        assert NOTE not in [r.getMessage() for r in caplog.records]

    def test_the_note_is_the_servers_constant(self):
        assert server.OLD_NAME_NOTE == NOTE
        assert "—" not in NOTE and "\n" not in NOTE

    def test_a_host_start_speaks_only_the_protocol(self, tmp_path):
        """A real stdio session through `python -m qualcoder_mcp.server`:
        the handshake succeeds (nothing else reached standard output),
        and the note is in the log a host keeps (standard error)."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        home = tmp_path / "home"
        home.mkdir()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-B", "-m", "qualcoder_mcp.server"],
            env=_env(home), cwd=str(tmp_path))
        log_path = tmp_path / "server.log"

        async def ask(log):
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return (await session.list_tools()).tools

        with open(log_path, "w", encoding="utf-8") as log:
            tools = asyncio.run(ask(log))
        assert len(tools) > 20
        assert NOTE in log_path.read_text(encoding="utf-8")


def _imports_of_the_old_package(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names
                      if a.name.split(".")[0] == "qualcoder_mcp"]
        elif isinstance(node, ast.ImportFrom) and node.module and \
                node.module.split(".")[0] == "qualcoder_mcp":
            found.append(node.module)
    return found


def test_only_this_module_imports_the_old_package():
    allowed = {Path(__file__).resolve()}
    offenders = []
    for folder in ("tests", "scripts", "src/exegete"):
        for path in sorted((REPO / folder).rglob("*.py")):
            if path.resolve() in allowed:
                continue
            if _imports_of_the_old_package(path):
                offenders.append(path.relative_to(REPO).as_posix())
    assert offenders == []


def test_the_hygiene_check_would_notice(tmp_path):
    sample = tmp_path / "t.py"
    sample.write_text("import qualcoder_mcp.server as s\n"
                      "from qualcoder_mcp import database\n",
                      encoding="utf-8")
    assert _imports_of_the_old_package(sample) == [
        "qualcoder_mcp.server", "qualcoder_mcp"]
