# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the transition check (the owner's rulings 42 and 43).

`exegete --check-transition` is read-only: it prints what the move from
qualcoder-mcp left behind and the one step that tidies each, and exits 0
when nothing is left. `--tidy` removes only the link at ~/.qualcoder_mcp
(never a folder) when it leads to ~/.exegete and nothing started as
qualcoder-mcp runs, and the old logs only with `--tidy-old-logs`.
Everything here runs in a home folder of its own under tmp_path, with
the hosts' files as fixtures; nothing reads the real ones.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import exegete.server as server
from exegete import env_settings, state_folder, transition

REPO = Path(__file__).resolve().parents[1]
POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="POSIX links")

# On Windows the check starts PowerShell to read the running programs,
# and PowerShell writes its own cache (its start-up profile data, its
# module analysis cache) under the profile folder it is given: in the
# command-line tests below, the scratch home. It also leaves an empty
# AppData\Roaming there (CI, 30 September). Those, and nothing else, may
# appear; Exegete itself writes nothing.
POWERSHELL_CACHE = ("AppData", "Local", "Microsoft", "Windows", "PowerShell")


def home_names(home: Path, windows=None):
    """The names at the top of `home`, less AppData on Windows once every
    path under it is shown to be PowerShell's cache or a folder on the
    way to it."""
    names = sorted(p.name for p in home.iterdir())
    if not (os.name == "nt" if windows is None else windows) or \
            "AppData" not in names:
        return names
    cache = home.joinpath(*POWERSHELL_CACHE)
    on_the_way = {home.joinpath(*POWERSHELL_CACHE[:n])
                  for n in range(2, len(POWERSHELL_CACHE))}
    on_the_way.add(home / "AppData" / "Roaming")     # empty: see above
    assert (home / "AppData").is_dir() and \
        not (home / "AppData").is_symlink()
    others = []                   # every one named, should any be found
    for root, folders, files in os.walk(home / "AppData"):
        for name in folders + files:
            path = Path(root) / name
            if path in on_the_way:
                if not path.is_dir() or path.is_symlink():
                    others.append(str(path))
            elif path != cache and cache not in path.parents:
                others.append(str(path))
    assert others == []
    names.remove("AppData")
    return names


def run(home, *, tidy=False, logs=False, lines=(), prefix=None,
        which=lambda name: None):
    out = io.StringIO()
    code = transition.run(
        tidy=tidy, tidy_old_logs=logs, out=out, home=home,
        prefix=prefix or home / "no-env", which=which,
        listing=(lambda: None) if lines is None else (lambda: list(lines)))
    return code, out.getvalue()


def env_with_old_package(root: Path, installer="pip", editable=False):
    info = root / "lib" / "python3.13" / "site-packages" / \
        "qualcoder_mcp-0.14.0a0.dist-info"
    info.mkdir(parents=True)
    (info / "INSTALLER").write_text(installer + "\n", encoding="utf-8")
    if editable:
        (info / "direct_url.json").write_text(json.dumps(
            {"url": "file:///src", "dir_info": {"editable": True}}),
            encoding="utf-8")
    (root / "bin").mkdir(exist_ok=True)
    return root


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_nothing_left(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    code, out = run(home)
    assert code == 0
    assert transition.NOTHING_LEFT in out
    assert sorted(p.name for p in home.iterdir()) == []       # read-only


class TestTheOldPackage:

    @pytest.mark.parametrize("installer,editable,step", [
        ("pip", False, '-m pip uninstall qualcoder-mcp'),
        ("uv", False, 'uv pip uninstall --python'),
        ("pip", True, '-m pip install -e .'),
    ])
    def test_in_this_environment(self, tmp_path, installer, editable, step):
        env = env_with_old_package(tmp_path / "venv", installer, editable)
        code, out = run(tmp_path / "home", prefix=env)
        assert code == 1
        assert f"still installed in {env}" in out
        assert step in out
        assert "First change every host entry" in out

    @pytest.mark.parametrize("tools,step", [
        (".local/share/uv/tools", "uv tool uninstall qualcoder-mcp"),
        (".local/pipx/venvs", "pipx uninstall qualcoder-mcp"),
    ])
    def test_as_a_tool(self, tmp_path, tools, step):
        home = tmp_path / "home"
        env_with_old_package(home / tools / "qualcoder-mcp")
        code, out = run(home)
        assert code == 1 and step in out

    def test_behind_the_command_on_the_path(self, tmp_path):
        env = env_with_old_package(tmp_path / "other-venv")
        command = write(env / "bin" / "qualcoder-mcp", "#!/bin/sh\n")
        code, out = run(tmp_path / "home", which=lambda name: str(command)
                        if name == "qualcoder-mcp" else None)
        assert code == 1 and str(env) in out


class TestTheHostsEntries:

    SECRET = "sk-not-to-be-printed"

    def _desktop(self, home):
        return write(home / "Library" / "Application Support" / "Claude" /
                     "claude_desktop_config.json", json.dumps({
                         "mcpServers": {
                             "qualcoder": {
                                 "command": "/v/bin/qualcoder-mcp",
                                 "env": {"QUALCODER_MCP_TOOLSET": "core",
                                         "API_KEY": self.SECRET}},
                             "by-module": {
                                 "command": "/v/bin/python",
                                 "args": ["-m", "qualcoder_mcp.server"]},
                             "by-uvx": {"command": "uvx",
                                        "args": ["qualcoder-mcp"]},
                             "from-a-clone": {
                                 "command": "uv",
                                 "args": ["run", "--directory",
                                          "/src/qualcoder-mcp",
                                          "qualcoder-mcp"]},
                             "already-new": {"command": "exegete"},
                             "unrelated": {"command": "npx",
                                           "args": ["other-server"]}},
                         "other": {"token": self.SECRET}}))

    def test_claude_desktop(self, tmp_path):
        home = tmp_path / "home"
        path = self._desktop(home)
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        code, out = run(home)
        assert code == 1
        flat = " ".join(out.split())
        for name, command, args in (
                ("qualcoder", "/v/bin/exegete", []),
                ("by-module", "/v/bin/python", ["-m", "exegete.server"]),
                ("by-uvx", "uvx", ["exegete"]),
                ("from-a-clone", "uv", ["run", "--directory",
                                        "/src/qualcoder-mcp", "exegete"])):
            assert (f'change the entry "{name}" to start '
                    f'{json.dumps(command)} with the arguments '
                    f'{json.dumps(args)}; keep its name') in flat, name
        assert '"already-new"' not in out and '"unrelated"' not in out
        assert "QUALCODER_MCP_TOOLSET becomes EXEGETE_TOOLSET" in flat
        assert self.SECRET not in out and "core" not in out
        assert (path.read_bytes(), path.stat().st_mtime_ns) == before

    def test_claude_code_lm_studio_and_codex(self, tmp_path):
        home = tmp_path / "home"
        write(home / ".claude.json", json.dumps({"projects": {
            "/some/project": {"mcpServers": {"qc": {
                "type": "stdio", "command": "qualcoder-mcp"}}}}}))
        write(home / ".lmstudio" / "mcp.json", json.dumps({"mcpServers": {
            "qualcoder": {"command": "uvx", "args": ["qualcoder-mcp"]}}}))
        write(home / ".codex" / "config.toml",
              '[mcp_servers.qualcoder]\ncommand = "qualcoder-mcp"\n'
              'args = []\n\n[mcp_servers.other]\ncommand = "x"\n')
        code, out = run(home)
        assert code == 1
        for label in ("Claude Code's entry \"qc\"",
                      "LM Studio's entry \"qualcoder\"",
                      "Codex's entry \"qualcoder\""):
            assert label in out, label
        assert '"other"' not in out

    def test_codex_on_python_3_10(self, tmp_path, monkeypatch):
        monkeypatch.setattr(transition, "tomllib", None)
        home = tmp_path / "home"
        write(home / ".codex" / "config.toml",
              '[mcp_servers."qualcoder"]\ncommand = "/v/bin/python"\n'
              'args = ["-m", "qualcoder_mcp.server"]\n')
        code, out = run(home)
        assert "Codex's entry \"qualcoder\"" in out
        assert '["-m", "exegete.server"]' in out

    def test_a_file_that_is_not_json_is_passed_over(self, tmp_path):
        home = tmp_path / "home"
        write(home / ".lmstudio" / "mcp.json", "{not json")
        assert run(home)[0] == 0


class TestTheLink:

    def _moved(self, home):
        new = home / ".exegete"
        new.mkdir(parents=True)
        (new / "preview_secret").write_text("k" * 64 + "\n",
                                            encoding="ascii")
        state_folder.make_link(new, home / ".qualcoder_mcp")
        return new

    def test_reported_and_left_without_tidy(self, tmp_path):
        self._moved(tmp_path)
        code, out = run(tmp_path)
        assert code == 1
        assert "the link the move left" in out
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")

    def test_tidy_removes_the_link_alone(self, tmp_path):
        new = self._moved(tmp_path)
        code, out = run(tmp_path, tidy=True)
        assert code == 0, out
        assert "Done: Removed the link" in out
        assert not os.path.lexists(tmp_path / ".qualcoder_mcp")
        assert (new / "preview_secret").read_text(encoding="ascii") == \
            "k" * 64 + "\n"
        assert run(tmp_path)[0] == 0              # nothing left now

    @pytest.mark.parametrize("lines", [
        ["/v/bin/python /v/bin/qualcoder-mcp"],
        ["/v/bin/python -m qualcoder_mcp.server"],
        None,                                     # the listing failed
    ])
    def test_kept_while_it_may_be_used(self, tmp_path, lines):
        self._moved(tmp_path)
        code, out = run(tmp_path, tidy=True, lines=lines)
        assert code == 1
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out

    def test_a_folder_is_never_removed(self, tmp_path):
        (tmp_path / ".exegete").mkdir()
        old = tmp_path / ".qualcoder_mcp"
        old.mkdir()
        (old / "preview_secret").write_text("x", encoding="ascii")
        code, out = run(tmp_path, tidy=True)
        assert code == 1
        assert "a folder of its own" in out and "never removes" in out
        assert (old / "preview_secret").is_file()

    @POSIX_ONLY
    def test_a_link_elsewhere_is_left(self, tmp_path):
        (tmp_path / ".exegete").mkdir()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        os.symlink(elsewhere, tmp_path / ".qualcoder_mcp")
        code, out = run(tmp_path, tidy=True)
        assert code == 1 and "does not lead to" in out
        assert os.path.islink(tmp_path / ".qualcoder_mcp")

    def test_what_counts_as_started_as_qualcoder_mcp(self):
        hits = transition.started_as_old([
            "/v/bin/python /v/bin/qualcoder-mcp",
            "python -m qualcoder_mcp.server",
            "uvx qualcoder-mcp",
            "C:\\v\\Scripts\\qualcoder-mcp.exe",
            "uv run --directory /x/local.mcpb.niccol-tempini.qualcoder-mcp "
            "exegete",
            "/v/bin/python -m exegete.server",
            "/usr/bin/vim notes-about-qualcoder-mcp.txt"])
        assert len(hits) == 4


class TestTheOldLogs:

    NAMES = ("mcp-server-qualcoder-mcp.log", "mcp-server-qualcoder-mcp1.log",
             "mcp-server-Exegete.log", "mcp-server-qualcoder.log",
             "mcp.log")

    def _logs(self, home):
        folder = home / "Library" / "Logs" / "Claude"
        for name in self.NAMES:
            write(folder / name, "log\n")
        return folder

    def test_listed_and_kept_by_tidy_alone(self, tmp_path):
        folder = self._logs(tmp_path)
        code, out = run(tmp_path, tidy=True)
        assert code == 1
        assert ("mcp-server-qualcoder-mcp.log, "
                "mcp-server-qualcoder-mcp1.log.") in out
        assert sorted(p.name for p in folder.iterdir()) == \
            sorted(self.NAMES)

    def test_removed_only_with_their_own_switch(self, tmp_path):
        folder = self._logs(tmp_path)
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 0, out
        assert sorted(p.name for p in folder.iterdir()) == sorted(
            ["mcp-server-Exegete.log", "mcp-server-qualcoder.log",
             "mcp.log"])

    def test_kept_while_an_old_copy_runs(self, tmp_path):
        folder = self._logs(tmp_path)
        code, _ = run(tmp_path, tidy=True, logs=True,
                      lines=["uvx qualcoder-mcp"])
        assert code == 1
        assert (folder / "mcp-server-qualcoder-mcp.log").is_file()


class TestTheEarlierProjectsFolder:

    def test_with_projects_it_needs_nothing(self, tmp_path):
        project = tmp_path / "Documents" / "Qualcoder MCP Projects" / \
            "Study.qda"
        project.mkdir(parents=True)
        (project / "data.qda").write_bytes(b"x")
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 0
        assert "holds 1 project(s)" in out and "Nothing to do" in out
        assert (project / "data.qda").read_bytes() == b"x"

    def test_empty_it_is_yours_to_remove(self, tmp_path):
        folder = tmp_path / "Documents" / "Qualcoder MCP Projects"
        folder.mkdir(parents=True)
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 1 and "never removes a folder" in out
        assert folder.is_dir()


class TestTheProcessList:
    """Whether an older copy runs is read from `ps` on macOS and Linux and
    from Windows PowerShell on Windows, started by its full path in the
    system folder: a bare name is looked up in the current folder first
    on Windows, so a powershell.exe where the check is run would be run.
    Without the system one nothing is read, so nothing is removed."""

    OUT = b"1 uvx qualcoder-mcp\n"

    def _run(self, monkeypatch):
        calls = []

        def run(cmd, **kwargs):
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, self.OUT, b"")
        monkeypatch.setattr(transition.subprocess, "run", run)
        return calls

    @staticmethod
    def _listing_as(monkeypatch, os_name):
        """_listing() with os.name set for the call alone: pytest itself
        must not see "nt" on macOS or Linux (pathlib would make Windows
        paths for its report of a failure)."""
        with monkeypatch.context() as patched:
            patched.setattr(os, "name", os_name)
            return transition._listing()

    def _windows(self, tmp_path):
        root = tmp_path / "Windows"
        exe = root / "System32" / "WindowsPowerShell" / "v1.0" / \
            "powershell.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
        return root, exe

    def test_windows_powershell_by_its_full_path(self, tmp_path,
                                                  monkeypatch):
        root, exe = self._windows(tmp_path)
        (tmp_path / "powershell.exe").write_bytes(b"")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SystemRoot", str(root))
        calls = self._run(monkeypatch)
        lines = self._listing_as(monkeypatch, "nt")
        assert [call[0] for call in calls] == [str(exe)]
        assert calls[0][1:3] == ["-NoProfile", "-Command"]
        assert lines == ["uvx qualcoder-mcp"]

    def test_without_it_nothing_is_read(self, tmp_path, monkeypatch):
        # a powershell.exe in the current folder is never the one run
        (tmp_path / "powershell.exe").write_bytes(b"")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
        calls = self._run(monkeypatch)
        assert self._listing_as(monkeypatch, "nt") is None
        assert calls == []

    @pytest.mark.parametrize("value", [None, "", "Windows", "."])
    def test_the_system_folder_is_a_full_path(self, tmp_path, monkeypatch,
                                              value):
        monkeypatch.chdir(tmp_path)
        if value is None:
            monkeypatch.delenv("SystemRoot", raising=False)
        else:
            monkeypatch.setenv("SystemRoot", value)
        assert env_settings.windows_system_root() == "C:\\Windows"
        monkeypatch.setenv("SystemRoot", str(tmp_path))
        assert env_settings.windows_system_root() == str(tmp_path)

    def test_ps_on_macos_and_linux(self, monkeypatch):
        calls = self._run(monkeypatch)
        assert self._listing_as(monkeypatch, "posix") == \
            ["uvx qualcoder-mcp"]
        assert calls == [["ps", "-axo", "pid=,args="]]


class TestTheCommandLine:

    def _run(self, home, *args, module="exegete.server"):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("QUALCODER", "EXEGETE"))}
        env.update(HOME=str(home), USERPROFILE=str(home),
                   PYTHONPATH=str(REPO / "src"))
        return subprocess.run([sys.executable, "-B", "-m", module, *args],
                              capture_output=True, text=True, env=env,
                              timeout=120, cwd=str(home))

    def test_it_never_moves_or_makes_the_state_folder(self, tmp_path):
        tmp_path = tmp_path / "home"
        old = tmp_path / ".qualcoder_mcp"
        old.mkdir(parents=True)
        (old / "preview_secret").write_text("k" * 64 + "\n",
                                            encoding="ascii")
        done = self._run(tmp_path, "--check-transition")
        assert done.returncode == 1, done.stderr
        assert transition.HEADING in done.stdout
        assert "has not been moved to" in done.stdout
        assert not os.path.lexists(tmp_path / ".exegete")
        assert not state_folder.is_link(old)
        # PowerShell's own cache aside, on Windows (home_names)
        assert home_names(tmp_path) == [".qualcoder_mcp"]

    def test_through_the_old_name(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        done = self._run(home, "--check-transition",
                         module="qualcoder_mcp.server")
        # 0, or 1 where the environment running the tests holds the old
        # package itself (the check then says so): never an error
        assert done.returncode in (0, 1), done.stderr
        assert transition.HEADING in done.stdout
        assert "Traceback" not in done.stderr
        # PowerShell's own cache aside, on Windows (home_names)
        assert home_names(home) == []

    @pytest.mark.parametrize("args", [["--tidy"], ["--tidy-old-logs"],
                                      ["--check-transition",
                                       "--tidy-old-logs"]])
    def test_the_switches_go_together(self, tmp_path, args):
        done = self._run(tmp_path, *args)
        assert done.returncode == 2
        assert "goes with" in done.stderr

    def test_the_old_commands_line_names_the_check(self):
        assert "`exegete --check-transition`" in server.OLD_NAME_NOTE
        assert "\n" not in server.OLD_NAME_NOTE


class TestTheHomeCheck:
    """home_names allows PowerShell's cache folder on Windows and nothing
    else, and nothing at all on macOS and Linux."""

    CACHED = POWERSHELL_CACHE + ("StartupProfileData-NonInteractive",)

    def _plant(self, home, parts, folder=False):
        path = home.joinpath(*parts)
        if folder:
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")

    def test_powershells_cache_alone_on_windows(self, tmp_path):
        home = tmp_path / "home"
        self._plant(home, self.CACHED)
        self._plant(home, POWERSHELL_CACHE + ("ModuleAnalysisCache",))
        (home / ".qualcoder_mcp").mkdir()
        assert home_names(home, windows=True) == [".qualcoder_mcp"]
        assert home_names(home, windows=False) == [".qualcoder_mcp",
                                                   "AppData"]

    def test_an_empty_roaming_folder_too(self, tmp_path):
        home = tmp_path / "home"
        self._plant(home, self.CACHED)
        self._plant(home, ("AppData", "Roaming"), folder=True)
        assert home_names(home, windows=True) == []
        self._plant(home, ("AppData", "Roaming", "x"))
        with pytest.raises(AssertionError):
            home_names(home, windows=True)

    @pytest.mark.skipif(os.name == "nt", reason="macOS and Linux only")
    def test_on_macos_and_linux_nothing_is_allowed(self, tmp_path):
        home = tmp_path / "home"
        self._plant(home, self.CACHED)
        assert home_names(home) == ["AppData"]

    @pytest.mark.parametrize("parts,folder", [
        (("AppData", "Roaming", "Claude", "claude_desktop_config.json"),
         False),
        (("AppData", "Local", "x"), False),
        (("AppData", "Local", "Microsoft", "Windows", "x"), False),
        (("AppData", "Local", "Microsoft", "Windows", "PowerShellX"), True),
        (("AppData", "x"), False),
    ])
    def test_anything_else_under_appdata_is_not(self, tmp_path, parts,
                                                folder):
        home = tmp_path / "home"
        self._plant(home, self.CACHED)
        self._plant(home, parts, folder)
        with pytest.raises(AssertionError):
            home_names(home, windows=True)


class TestTheHelpTopic:

    def test_the_assistant_can_read_it(self):
        topic = json.loads(server.explain_ai_coding_tools(
            "moving_from_qualcoder_mcp"))
        flat = " ".join(json.dumps(topic).split())
        assert topic["title"] == "Moving from qualcoder-mcp to Exegete"
        for words in ("exegete --check-transition", "--tidy",
                      "--tidy-old-logs", "paste", "Never suggest deleting "
                      "a folder", "exit code 0"):
            assert words in flat, words
        overview = json.loads(server.explain_ai_coding_tools())
        assert "moving_from_qualcoder_mcp" in overview[
            "moving_from_qualcoder_mcp"]
        unknown = json.loads(server.explain_ai_coding_tools("nope"))
        assert "moving_from_qualcoder_mcp" in unknown["available_tools"]


def test_the_documents_point_to_the_check():
    def flat(name):
        return " ".join((REPO / name).read_text(encoding="utf-8").split())
    install = flat("INSTALL.md")
    section = install[install.index("## Coming from qualcoder-mcp"):]
    section = section[:section.index("## Upgrading from an earlier")]
    assert "`exegete --check-transition`" in section
    assert "last release will say plainly that it is the last" in section
    unreleased = flat("CHANGELOG.md").split("## [0.14.0")[0]
    assert "exegete --check-transition" in unreleased
    assert "`--tidy`" in unreleased
    old = flat("packaging/pypi-old-name/README.md")
    assert "`exegete --check-transition`" in old
    assert "last release of this package will say plainly" in old
