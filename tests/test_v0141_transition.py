# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1: the transition check.

`exegete --check-transition` is read-only: it prints what the move from
qualcoder-mcp left behind and the steps that tidy it, in the order to
take them, and exits 0 when nothing is left. `--tidy` removes only the
link at ~/.qualcoder_mcp (never a folder) when it leads to ~/.exegete,
nothing started as qualcoder-mcp runs and nothing is left that could
start an older copy; the old logs go only with `--tidy-old-logs`.
Everything here runs in a home folder of its own under tmp_path, with
the hosts' files as fixtures; nothing reads the real ones.
"""

import io
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import exegete.server as server
from exegete import env_settings, state_folder, transition
from exegete.transition import command_line, quoted

try:
    import tomllib
except ModuleNotFoundError:                    # Python 3.10
    tomllib = None

REPO = Path(__file__).resolve().parents[1]
POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="POSIX links")
BIN = "Scripts" if os.name == "nt" else "bin"
# A folder name with a space and both quotes (Windows allows no double
# quote in a name, so there it has the single one only).
ODD = "my venv's copy" if os.name == "nt" else "my venv's \"copy\""

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


def items(out):
    """The report's numbered items: [(what, [the lines under it])]."""
    found = []
    for line in out.splitlines():
        if line[:1].isdigit() and ". " in line:
            found.append((line.split(". ", 1)[1], []))
        elif line.startswith("   ") and found:
            found[-1][1].append(line)
    return found


def pasted(out):
    """The lines printed to be pasted (commands, entry lines), in order."""
    return [line[7:] for line in out.splitlines()
            if line.startswith("       ") and line[7:8] != " "]


def env_with_old_package(root: Path, installer="pip", editable=False,
                         version="0.14.0a0", exegete=False, url=None):
    """`url`: the copy of the source an editable install came from, as
    pip records it (a folder that does not exist by default)."""
    site = root / "lib" / "python3.13" / "site-packages"
    info = site / f"qualcoder_mcp-{version}.dist-info"
    info.mkdir(parents=True)
    (info / "INSTALLER").write_text(installer + "\n", encoding="utf-8")
    if editable:
        (info / "direct_url.json").write_text(json.dumps(
            {"url": url or "file:///no-such-source",
             "dir_info": {"editable": True}}), encoding="utf-8")
    if exegete:
        (site / f"exegete-{version}.dist-info").mkdir()
    (root / "bin").mkdir(exist_ok=True)
    return root


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def desktop_file(home: Path, servers: dict) -> Path:
    return write(home / "Library" / "Application Support" / "Claude" /
                 "claude_desktop_config.json",
                 json.dumps({"mcpServers": servers}))


def test_nothing_left(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    code, out = run(home)
    assert code == 0
    assert transition.NOTHING_LEFT in out
    assert sorted(p.name for p in home.iterdir()) == []       # read-only


class TestTheOldPackage:

    @pytest.mark.parametrize("installer,editable", [
        ("pip", False), ("uv", False), ("pip", True)])
    def test_in_this_environment(self, tmp_path, installer, editable):
        env = env_with_old_package(tmp_path / "venv", installer, editable,
                                   version="0.14.1a0", exegete=True)
        code, out = run(tmp_path / "home", prefix=env)
        assert code == 1
        assert f"still installed in {quoted(str(env))}" in out
        python = str(env / "bin" / "python")
        remove = (["uv", "pip", "uninstall", "--python", python,
                   "qualcoder-mcp"] if installer == "uv"
                  else [python, "-m", "pip", "uninstall", "qualcoder-mcp"])
        expected = [command_line(remove)]
        if editable:
            expected.append(command_line([python, "-m", "pip", "install",
                                          "-e", "."]))
        assert pasted(out) == expected
        assert "Once no host entry starts it any more" in out

    @pytest.mark.parametrize("editable", [False, True])
    def test_an_earlier_release_gets_exegete_first(self, tmp_path, editable):
        env = env_with_old_package(tmp_path / "venv", editable=editable)
        code, out = run(tmp_path / "home", prefix=env)
        python = str(env / "bin" / "python")
        install = command_line([python, "-m", "pip", "install", "exegete"])
        remove = command_line([python, "-m", "pip", "uninstall",
                               "qualcoder-mcp"])
        if editable:
            # where the copy is cannot be told here: "its folder"
            again = command_line([python, "-m", "pip", "install", "-e", "."])
            assert pasted(out) == ["git pull", again, remove, again]
            assert "This comes first. Quit your AI host, since" in \
                items(out)[0][1][0]
            assert "Quit your AI host first" not in out
            assert "in its folder" in items(out)[0][1][0]
        else:
            assert pasted(out) == [install, remove]
        assert "This comes first" in items(out)[0][1][0]

    def test_behind_the_command_on_the_path(self, tmp_path):
        env = env_with_old_package(tmp_path / "other-venv")
        command = write(env / "bin" / "qualcoder-mcp", "#!/bin/sh\n")
        code, out = run(tmp_path / "home", which=lambda name: str(command)
                        if name == "qualcoder-mcp" else None)
        assert code == 1 and quoted(str(env)) in out


class TestACopyOfTheSource:
    """INSTALL's git route (and the owner's own set-up): a clone with its
    environment inside it, installed editable at 0.14.0, and a host entry
    that starts that environment's Python with the old module."""

    def _clone(self, tmp_path, url=True, pyproject=True, inside=True):
        """`inside`: the environment is the clone's own `venv`, else one
        elsewhere in the home folder."""
        home = tmp_path / "home"
        clone = home / "Documents" / ODD
        if pyproject:
            write(clone / "pyproject.toml", "[project]\n")
        env = env_with_old_package(
            clone / "venv" if inside else home / "venvs" / "qc",
            editable=True, url=clone.as_uri() if url else None)
        write(env / "bin" / "python", "")
        return home, clone, env

    @pytest.mark.parametrize("url,inside", [
        (True, False),               # pip's record alone can tell
        (True, True), (False, True)  # or else the environment's parent
    ])
    def test_quit_first_and_the_folder_named(self, tmp_path, url, inside):
        home, clone, env = self._clone(tmp_path, url=url, inside=inside)
        code, out = run(home, prefix=env)
        what, lines = items(out)[0]
        step = " ".join(" ".join(lines).split())
        assert "installed from a copy of the source" in what
        assert "This comes first. Quit your AI host, since" in step
        assert "Quit your AI host first" not in step
        assert quoted("~" + os.sep + os.path.join("Documents", ODD)) in step
        python = str(env / "bin" / "python")
        assert pasted(out)[:2] == [
            command_line(["git", "-C", str(clone), "pull"]),
            command_line([python, "-m", "pip", "install", "-e",
                          str(clone)])]
        assert pasted(out)[-1] == command_line(
            [python, "-m", "pip", "install", "-e", str(clone)])
        assert "git pull" not in pasted(out)
        assert all(" -e ." not in line for line in pasted(out))

    def test_a_parent_without_pyproject_is_not_taken(self, tmp_path):
        home, clone, env = self._clone(tmp_path, url=False, pyproject=False)
        code, out = run(home, prefix=env)
        assert pasted(out)[0] == "git pull"
        assert "in its folder" in items(out)[0][1][0]

    def test_the_entry_waits_for_exegete_in_its_python(self, tmp_path):
        home, clone, env = self._clone(tmp_path)
        python = str(env / "bin" / "python")
        desktop_file(home, {"qualcoder": {
            "command": python, "args": ["-m", "qualcoder_mcp.server"]}})
        code, out = run(home, prefix=env)
        entry = [lines for what, lines in items(out)
                 if "still starts the old command" in what][0]
        step = " ".join(" ".join(entry).split())
        assert "only after the step above that installs Exegete" in step
        assert f"the Python it starts, {quoted(python)}, has no Exegete " \
            "yet" in step
        assert "does not exist" not in out


class TestRealPaths:
    """What the researcher pastes carries full paths, quoted for the
    shell or the file it goes into; `~` is for prose only. Names and
    paths read from files and folders are shown as JSON strings."""

    def test_commands_carry_full_paths(self, tmp_path):
        home = tmp_path / "home o'brien"
        env = env_with_old_package(home / ODD)
        code, out = run(home, prefix=env)
        python = str(env / "bin" / "python")
        argvs = [[python, "-m", "pip", "install", "exegete"],
                 [python, "-m", "pip", "uninstall", "qualcoder-mcp"]]
        assert pasted(out) == [command_line(a) for a in argvs]
        # (a short name such as RUNNER~1 may be in the temporary folder's
        # path on Windows: only ~ followed by a separator is the home's)
        assert all("~" + os.sep not in line for line in pasted(out))
        assert quoted("~" + os.sep + ODD) in out           # prose alone
        if os.name != "nt":
            assert [shlex.split(line) for line in pasted(out)] == argvs

    @POSIX_ONLY
    def test_a_pasted_command_runs(self, tmp_path):
        home = tmp_path / "home o'brien"
        env = env_with_old_package(home / ODD)
        python = write(env / "bin" / "python",
                       "#!/bin/sh\nprintf '%s\\n' \"$@\" >> "
                       "\"$(dirname \"$0\")/ran.txt\"\n")
        python.chmod(0o755)
        code, out = run(home, prefix=env)
        for line in pasted(out):
            for shell in ("/bin/sh", "/bin/bash", "/bin/zsh"):
                if os.path.exists(shell):
                    done = subprocess.run([shell, "-c", line], cwd=tmp_path,
                                          capture_output=True, timeout=30)
                    assert done.returncode == 0, (shell, line, done.stderr)
        ran = (env / "bin" / "ran.txt").read_text(encoding="utf-8")
        assert "-m\npip\ninstall\nexegete\n" in ran
        assert "-m\npip\nuninstall\nqualcoder-mcp\n" in ran

    def test_entries_carry_full_paths(self, tmp_path):
        home = tmp_path / "home o'brien"
        env = env_with_old_package(home / ODD, version="0.14.1a0",
                                   exegete=True)
        for name in ("qualcoder-mcp", "exegete", "python"):
            write(env / "bin" / name, "")
        old = str(env / "bin" / "qualcoder-mcp")
        desktop_file(home, {
            "qualcoder": {"command": old},
            "by-module": {"command": str(env / "bin" / "python"),
                          "args": ["-m", "qualcoder_mcp.server"]}})
        write(home / ".codex" / "config.toml",
              f"[mcp_servers.qc]\ncommand = {json.dumps(old)}\n")
        code, out = run(home)
        lines = pasted(out)
        desktop = [json.loads("{" + a + " " + b + "}")
                   for a, b in zip(lines, lines[1:])
                   if a.startswith('"command"')]
        assert desktop == [
            {"command": str(env / "bin" / "exegete"), "args": []},
            {"command": str(env / "bin" / "python"),
             "args": ["-m", "exegete.server"]}]
        codex = [a + "\n" + b for a, b in zip(lines, lines[1:])
                 if a.startswith("command =")]
        assert len(codex) == 1
        if tomllib is not None:
            assert tomllib.loads(codex[0]) == {
                "command": str(env / "bin" / "exegete"), "args": []}
        assert "does not exist" not in out           # it does, already
        assert all("~" + os.sep not in line for line in lines)

    def test_names_are_shown_safely(self, tmp_path):
        home = tmp_path / "home"
        name = "evil\n2. Nothing is left behind.\x1b[2J‮"
        desktop_file(home, {name: {"command": "uvx",
                                   "args": ["qualcoder-mcp"]}})
        folder = "v\nw" if os.name != "nt" else "v w"
        env = env_with_old_package(home / folder, version="0.14.1a0",
                                   exegete=True)
        code, out = run(home, prefix=env)
        assert "\x1b" not in out and "‮" not in out
        assert len(items(out)) == 2                  # the entry, the package
        assert quoted(name) in out
        assert quoted("~" + os.sep + folder) in out
        for line in out.splitlines():
            assert line in ("", transition.HEADING) or \
                line[:3] in ("1. ", "2. ", "   ") or \
                line.startswith("Read-only unless"), line


class TestShells:
    """Commands for PowerShell on Windows (a quoted program needs `&`;
    every quote PowerShell reads as a single one is doubled), and for
    sh, bash and zsh elsewhere; a character that cannot be shown as it is
    is escaped, never printed raw."""

    def test_powershell(self):
        python = "C:\\Users\\o'brien\\my venv\\Scripts\\python.exe"
        assert command_line([python, "-m", "pip", "uninstall",
                             "qualcoder-mcp"], windows=True) == (
            "& 'C:\\Users\\o''brien\\my venv\\Scripts\\python.exe' "
            "-m pip uninstall qualcoder-mcp")
        assert command_line(["uv", "tool", "install", "exegete"],
                            windows=True) == "uv tool install exegete"
        assert command_line(["C:\\v\\python.exe", "-m", "x"],
                            windows=True) == "C:\\v\\python.exe -m x"
        assert command_line(["a\u2019b c"], windows=True) == \
            "& 'a\u2019\u2019b c'"
        assert command_line(["a$b`c\u202e"], windows=True) == \
            '& "a`$b``c$([char]::ConvertFromUtf32(0x202e))"'
        assert transition._shell(windows=True) == "In PowerShell"
        assert transition._shell(windows=False) == "In a terminal"

    def test_sh(self):
        assert command_line(["/v/my \"x\" o'b/python", "-m", "pip"],
                            windows=False) == \
            "'/v/my \"x\" o'\"'\"'b/python' -m pip"
        assert command_line(["/v/a\nb'c/python"], windows=False) == \
            "$'/v/a\\x0ab\\'c/python'"
        assert "\n" not in command_line(["/v/a\u2028b"], windows=False)

    def test_invisible_characters_as_their_utf8_bytes(self):
        # the Mac's bash 3.2 and sh know \x but not \u or \U
        assert command_line(["/v/a\u00a0b/python"], windows=False) == \
            "$'/v/a\\xc2\\xa0b/python'"
        assert command_line(["/v/\u200fx"], windows=False) == \
            "$'/v/\\xe2\\x80\\x8fx'"
        assert command_line(["/v/\U000e0001"], windows=False) == \
            "$'/v/\\xf3\\xa0\\x80\\x81'"
        if os.name != "nt":
            # a byte the file system gave that is not UTF-8 stays that byte
            assert command_line([os.fsdecode(b"/v/\xff")],
                                windows=False) == "$'/v/\\xff'"

    @POSIX_ONLY
    @pytest.mark.parametrize("name", ["a\u00a0b", "\u200fx", "o'b\u00a0\"c"])
    def test_invisible_characters_paste_in_every_shell(self, tmp_path, name):
        folder = tmp_path / name
        folder.mkdir()
        show = write(folder / "show", "#!/bin/sh\nprintf '%s' \"$0\" > "
                     "\"$(dirname \"$0\")/ran.txt\"\n")
        show.chmod(0o755)
        line = command_line([str(show)], windows=False)
        shells = [s for s in ("/bin/bash", "/bin/zsh", "/bin/sh")
                  if os.path.exists(s) and "dash" not in
                  os.path.realpath(s)]
        for shell in shells:
            (folder / "ran.txt").unlink(missing_ok=True)
            done = subprocess.run([shell, "-c", line], capture_output=True,
                                  timeout=30)
            assert done.returncode == 0, (shell, line, done.stderr)
            assert (folder / "ran.txt").read_bytes() == \
                os.fsencode(str(show)), shell

    def test_quoted_is_json(self):
        for text in ("plain", "a\nb", "\x1b[2J", "\u202e", "a\"b\\c",
                     "\U000e0001"):
            assert json.loads(quoted(text)) == text
            assert quoted(text).isprintable()
        if tomllib is not None:
            assert tomllib.loads("a = " + quoted("x\U000e0001\n",
                                                 toml=True)) == \
                {"a": "x\U000e0001\n"}


TOOLS = {"uv tool": (".local/share/uv/tools", ["uv", "tool"]),
         "pipx": (".local/pipx/venvs", ["pipx"])}


def lay_out_tool(home, kind, dist, version, inner_exegete=False):
    """A tool's environment and command as uv tool or pipx leave them:
    the environment in the tool folder, its own commands linked from
    ~/.local/bin (copied, on Windows). `inner_exegete`: the environment
    also holds exegete, as `uv tool upgrade qualcoder-mcp` to 0.14.1
    leaves it, without linking its command."""
    root = home / TOOLS[kind][0] / dist
    site = root / "lib" / "python3.13" / "site-packages"
    (site / f"{dist.replace('-', '_')}-{version}.dist-info").mkdir(
        parents=True)
    own = [dist]
    if inner_exegete:
        (site / f"exegete-{version}.dist-info").mkdir()
        write(root / BIN / "exegete", "#!/bin/sh\n")
    for command in own:
        target = write(root / BIN / command, "#!/bin/sh\n")
        link = home / ".local" / "bin" / command
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            link.write_bytes(target.read_bytes())
        else:
            os.symlink(target, link)
    return root


def remove_tool(home, kind, dist):
    import shutil
    shutil.rmtree(home / TOOLS[kind][0] / dist)
    (home / ".local" / "bin" / dist).unlink()


class TestInstallFirst:
    """For uv tool and pipx installs: installing exegete comes first, the
    entries follow and point at a command that then exists, and the old
    package goes last, so following the steps in order never leaves the
    host without a server. The installers' work is laid out here as they
    leave it; test_v0141_transition_installers.py runs the real ones."""

    @pytest.mark.parametrize("kind", ["uv tool", "pipx"])
    @pytest.mark.parametrize("version", ["0.14.0a0", "0.14.1a0"])
    def test_following_the_steps_in_order(self, tmp_path, kind, version):
        home = tmp_path / "home"
        lay_out_tool(home, kind, "qualcoder-mcp", version,
                     inner_exegete=version != "0.14.0a0")
        old = home / ".local" / "bin" / "qualcoder-mcp"
        config = desktop_file(home, {"qualcoder": {"command": str(old)}})
        install = command_line(TOOLS[kind][1] + ["install", "exegete"])
        remove = command_line(TOOLS[kind][1] + ["uninstall",
                                                "qualcoder-mcp"])
        code, out = run(home)
        found = items(out)
        assert pasted(out)[0] == install and pasted(out)[-1] == remove
        assert "This comes first" in found[0][1][0]
        assert "still starts the old command" in found[1][0]
        assert "only after the step above that installs Exegete" in \
            found[1][1][0]
        assert "still installed" in found[2][0]
        # 1. installing exegete, as the installer does
        lay_out_tool(home, kind, "exegete", "0.14.1a0")
        code, out = run(home)
        assert install not in pasted(out) and "only after" not in out
        # 2. the entry, as printed
        entry = json.loads("{" + " ".join(
            line for line in pasted(out) if line.startswith('"')) + "}")
        assert Path(entry["command"]).is_file()
        config.write_text(json.dumps({"mcpServers": {"qualcoder": entry}}),
                          encoding="utf-8")
        code, out = run(home)
        assert "still starts the old command" not in out
        assert pasted(out) == [remove]
        # 3. removing the old package, as the installer does
        remove_tool(home, kind, "qualcoder-mcp")
        code, out = run(home)
        assert code == 0 and transition.NOTHING_LEFT in out
        started = json.loads(config.read_text(encoding="utf-8"))
        assert Path(started["mcpServers"]["qualcoder"]["command"]).is_file()

    @pytest.mark.parametrize("kind", ["uv tool", "pipx"])
    def test_exegete_already_installed(self, tmp_path, kind):
        home = tmp_path / "home"
        lay_out_tool(home, kind, "qualcoder-mcp", "0.14.1a0", True)
        lay_out_tool(home, kind, "exegete", "0.14.1a0")
        desktop_file(home, {"qualcoder": {
            "command": str(home / ".local" / "bin" / "qualcoder-mcp")}})
        code, out = run(home)
        assert "This comes first" not in out and "does not exist" not in out
        assert "still starts the old command" in items(out)[0][0]

    @POSIX_ONLY
    @pytest.mark.parametrize("kind", ["uv tool", "pipx"])
    @pytest.mark.parametrize("bare", [False, True])
    def test_a_command_from_inside_the_old_tool_is_not_counted(
            self, tmp_path, kind, bare):
        # `pipx install --include-deps` and `pipx inject --include-apps`
        # link exegete's command from the old package's own environment,
        # which removing the old package takes with it
        home = tmp_path / "home"
        root = lay_out_tool(home, kind, "qualcoder-mcp", "0.14.1a0",
                            inner_exegete=True)
        folder = home / ".local" / "bin"
        os.symlink(root / BIN / "exegete", folder / "exegete")
        desktop_file(home, {"qualcoder": {
            "command": "qualcoder-mcp" if bare else
            str(folder / "qualcoder-mcp")}})

        def which(name):
            return str(folder / name) if (folder / name).exists() else None
        code, out = run(home, which=which)
        # the real pipx will not replace a command linked from another
        # environment without --force (neither will uv)
        install = command_line(TOOLS[kind][1] + ["install", "--force",
                                                 "exegete"])
        remove = command_line(TOOLS[kind][1] + ["uninstall",
                                                "qualcoder-mcp"])
        assert pasted(out)[0] == install and pasted(out)[-1] == remove
        flat = " ".join(out.split())
        assert "only after the step above that installs Exegete" in flat
        assert (f"{quoted(str(folder / 'exegete'))} leads into the old "
                f"package's environment") in flat
        assert (f"the exegete command at {quoted(str(folder / 'exegete'))} "
                f"leads into the old package's own environment") in flat
        assert "does not exist" not in flat

    def test_an_entry_never_points_at_nothing(self, tmp_path):
        home = tmp_path / "home"
        old = write(home / "custom" / "qualcoder-mcp", "")
        desktop_file(home, {"qualcoder": {"command": str(old)}})
        code, out = run(home)
        assert (f"{quoted(str(home / 'custom' / 'exegete'))} does not "
                f"exist yet: install Exegete") in out


class TestTheHostsEntries:

    SECRET = "sk-not-to-be-printed"

    def _desktop(self, home):
        return desktop_file(home, {
            "qualcoder": {
                "command": "/v/bin/qualcoder-mcp",
                "env": {"QUALCODER_MCP_TOOLSET": "core",
                        "API_KEY": self.SECRET}},
            "by-module": {
                "command": "/v/bin/python",
                "args": ["-m", "qualcoder_mcp.server"]},
            "by-uvx": {"command": "uvx", "args": ["qualcoder-mcp"]},
            "pinned": {"command": "uvx", "args": ["qualcoder-mcp@0.14.0"]},
            "from-a-clone": {
                "command": "uv",
                "args": ["run", "--directory", "/src/qualcoder-mcp",
                         "qualcoder-mcp"]},
            "already-new": {"command": "exegete"},
            "unrelated": {"command": "npx", "args": ["other-server"]}})

    def test_claude_desktop(self, tmp_path):
        home = tmp_path / "home"
        path = self._desktop(home)
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        code, out = run(home)
        assert code == 1
        lines = pasted(out)
        entries = [json.loads("{" + a + " " + b + "}")
                   for a, b in zip(lines, lines[1:])
                   if a.startswith('"command"')]
        assert entries == [
            {"command": "/v/bin/exegete", "args": []},
            {"command": "/v/bin/python", "args": ["-m", "exegete.server"]},
            {"command": "uvx", "args": ["exegete"]},
            {"command": "uvx", "args": ["exegete"]},
            {"command": "uv", "args": ["run", "--directory",
                                       "/src/qualcoder-mcp", "exegete"]}]
        assert '"already-new"' not in out and '"unrelated"' not in out
        assert "QUALCODER_MCP_TOOLSET becomes EXEGETE_TOOLSET" in out
        assert self.SECRET not in out and "core" not in out
        assert (path.read_bytes(), path.stat().st_mtime_ns) == before
        # none of these commands exists here: each says what comes first
        flat = " ".join(out.split())
        assert '"/v/bin/exegete" does not exist yet' in flat
        assert "The Python it starts has no Exegete yet" in flat
        assert '"/src/qualcoder-mcp" has no Exegete yet' in flat

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
        assert 'command = "exegete"' in pasted(out)

    def test_codex_on_python_3_10(self, tmp_path, monkeypatch):
        monkeypatch.setattr(transition, "tomllib", None)
        home = tmp_path / "home"
        write(home / ".codex" / "config.toml",
              '[mcp_servers."qualcoder"]\ncommand = "/v/bin/python"\n'
              'args = ["-m", "qualcoder_mcp.server"]\n')
        code, out = run(home)
        assert "Codex's entry \"qualcoder\"" in out
        assert 'args = ["-m", "exegete.server"]' in pasted(out)

    @pytest.mark.parametrize("where,text", [
        (".lmstudio/mcp.json", "{not json"),
        (".lmstudio/mcp.json", "[" * 200000 + "]" * 200000),
        (".lmstudio/mcp.json", '{"mcpServers": ' + "[" * 200000 + "]" *
         200000 + "}"),
        (".claude.json", '{"projects": ["not", "a", "table"]}'),
        (".claude.json", '{"projects": {"p": {"mcpServers": ["x"]}}}'),
        (".codex/config.toml", "a = " + "[" * 200000 + "]" * 200000),
        (".codex/config.toml", "[mcp_servers.qc]\ncommand = [\n"),
    ], ids=["not-json", "deep-json", "deep-table", "projects-a-list",
            "servers-a-list", "deep-toml", "broken-toml"])
    def test_a_malformed_file_is_passed_over(self, tmp_path, where, text):
        home = tmp_path / "home"
        write(home / where, text)
        assert run(home)[0] == 0

    def test_a_deep_line_on_python_3_10(self, tmp_path, monkeypatch):
        monkeypatch.setattr(transition, "tomllib", None)
        home = tmp_path / "home"
        write(home / ".codex" / "config.toml", "[mcp_servers.qc]\nargs = " +
              "[" * 200000 + "]" * 200000 + "\n")
        assert run(home)[0] == 0

    def test_pinned_and_extra_forms(self):
        new = transition.old_entry
        assert new({"command": "uvx", "args": ["qualcoder-mcp==0.14.0"]}) \
            == ("uvx", ["exegete"])
        assert new({"command": "uvx", "args": [
            "--from", "qualcoder-mcp[x]>=0.13", "qualcoder-mcp"]}) == \
            ("uvx", ["--from", "exegete", "exegete"])
        assert new({"command": "C:\\v\\Scripts\\qualcoder-mcp.exe"}) == \
            ("C:\\v\\Scripts\\exegete.exe", [])
        assert new({"command": "uvx", "args": ["qualcoder-mcp-extra"]}) \
            is None


EXTENSION_ID = "local.mcpb.niccol-tempini.qualcoder-mcp"


def extension(home, version="0.14.0-alpha", code=("qualcoder_mcp",),
              windows=False, manifest=True, name="qualcoder-mcp",
              folder=EXTENSION_ID):
    """An extension unpacked where Claude Desktop keeps them (macOS, or
    Windows with `windows`), as the published 0.14.0 package lays it
    out: its manifest and the server's code under src/."""
    base = (home / "AppData" / "Roaming" / "Claude" if windows else
            home / "Library" / "Application Support" / "Claude")
    folder = base / "Claude Extensions" / folder
    if manifest:
        write(folder / "manifest.json", json.dumps({
            "manifest_version": "0.2", "name": name, "version": version,
            "server": {"type": "uv",
                       "entry_point": f"src/{code[-1]}/server.py"}}))
    for package in code:
        write(folder / "src" / package / "server.py", "")
    return folder


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
        ["/v/bin/uv tool uvx qualcoder-mcp@0.14.0"],
        None,                                     # the listing failed
    ])
    def test_kept_while_it_may_be_used(self, tmp_path, lines):
        self._moved(tmp_path)
        code, out = run(tmp_path, tidy=True, lines=lines)
        assert code == 1
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out

    @pytest.mark.parametrize("kind", ["uv tool", "pipx"])
    def test_kept_while_an_older_package_is_installed(self, tmp_path, kind):
        self._moved(tmp_path)
        lay_out_tool(tmp_path, kind, "qualcoder-mcp", "0.14.0a0")
        code, out = run(tmp_path, tidy=True)
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out
        link = [what for what, _ in items(out) if "the link" in what][0]
        assert "an older copy could still be started: qualcoder-mcp " \
            "0.14.0a0 in" in link
        assert "second secret key" in out

    def test_kept_while_an_entry_starts_the_old_command(self, tmp_path):
        self._moved(tmp_path)
        desktop_file(tmp_path, {"qualcoder": {
            "command": "uvx", "args": ["qualcoder-mcp==0.14.0"]}})
        code, out = run(tmp_path, tidy=True)
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out
        assert "Claude Desktop's entry \"qualcoder\"." in out

    @pytest.mark.parametrize("windows", [False, True])
    def test_kept_while_an_older_desktop_extension_is_installed(
            self, tmp_path, windows):
        self._moved(tmp_path)
        folder = extension(tmp_path, windows=windows)
        code, out = run(tmp_path, tidy=True)
        assert code == 1
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out
        found = dict(items(out))
        shown = quoted("~" + os.sep + str(folder.relative_to(tmp_path)))
        older = [what for what in found if "desktop extension" in what and
                 "the link" not in what]
        assert len(older) == 1 and shown in older[0]
        assert "0.14.0-alpha" in older[0]
        assert "Update it" in found[older[0]][0]
        link = [what for what in found if "the link" in what][0]
        assert ("an older copy could still be started: the desktop "
                "extension, qualcoder-mcp 0.14.0-alpha, in " + shown) in link

    @pytest.mark.parametrize("layout", [
        dict(manifest=False),                          # its code alone
        dict(name="something-else"),                   # its code alone
        dict(code=("exegete",)),                       # its manifest alone
        dict(version="an unreadable version", code=("exegete",)),
    ])
    def test_its_code_or_its_manifest_is_enough(self, tmp_path, layout):
        self._moved(tmp_path)
        extension(tmp_path, **layout)
        code, out = run(tmp_path, tidy=True)
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out and "desktop extension" in out

    @pytest.mark.parametrize("layout", [
        dict(version="0.14.1-alpha", code=("exegete",)),
        # unpacked over the old folder, which kept the old code
        dict(version="0.14.1-alpha", code=("qualcoder_mcp", "exegete")),
        dict(version="0.15.0-alpha", code=("exegete",)),
        dict(name="another-server", code=("another",),
             folder="local.mcpb.someone.another-server"),
    ])
    def test_an_updated_or_another_extension_does_not(self, tmp_path,
                                                      layout):
        self._moved(tmp_path)
        extension(tmp_path, **layout)
        code, out = run(tmp_path, tidy=True)
        assert "Done: Removed the link" in out, out
        assert "desktop extension" not in out

    def test_the_tidy_says_what_it_cannot_see(self, tmp_path):
        self._moved(tmp_path)
        code, out = run(tmp_path)
        link = [lines for what, lines in items(out) if "the link" in what][0]
        flat = " ".join(" ".join(link).split())
        assert "--tidy` removes the link" in flat
        assert ("This check cannot see an older copy started from a "
                "project's own .mcp.json file: keep the link while one "
                "could still start.") in flat

    def test_a_pointer_package_alone_does_not_hold_it(self, tmp_path):
        self._moved(tmp_path)
        env = env_with_old_package(tmp_path / "venv", version="0.14.1a0",
                                   exegete=True)
        code, out = run(tmp_path, tidy=True, prefix=env)
        assert "Done: Removed the link" in out
        assert not os.path.lexists(tmp_path / ".qualcoder_mcp")

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
            "uvx qualcoder-mcp==0.14.0",
            "uvx qualcoder-mcp@0.14.0",
            "uv tool uvx --from 'qualcoder-mcp>=0.13' qualcoder-mcp",
            "uv run --directory /x/local.mcpb.niccol-tempini.qualcoder-mcp "
            "exegete",
            "/v/bin/python -m exegete.server",
            "uvx qualcoder-mcp-extra",
            "/usr/bin/vim notes-about-qualcoder-mcp.txt"])
        assert len(hits) == 7


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
    """Searched as list_available_projects searches (any project up to
    three levels down); never offered for removal while anything at all
    is in it, and what is there is named."""

    FOLDER = ("Documents", "Qualcoder MCP Projects")

    def _project(self, home, *parts):
        project = home.joinpath(*self.FOLDER, *parts)
        project.mkdir(parents=True)
        (project / "data.qda").write_bytes(b"x")
        return project

    def test_with_projects_it_needs_nothing(self, tmp_path):
        project = self._project(tmp_path, "Study.qda")
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 0
        assert "holds 1 project, up to" in out and "Nothing to do" in out
        assert (project / "data.qda").read_bytes() == b"x"

    def test_counts_read_plainly(self, tmp_path):
        self._project(tmp_path, "One.qda")
        self._project(tmp_path, "Two.qda")
        self._project(tmp_path, "old", "One_backup_20250101_1200.qda")
        code, out = run(tmp_path)
        assert "holds 2 projects, up to" in out
        assert "1 backup: " in out
        assert "(s)" not in out
        self._project(tmp_path, "old", "Two_backup_20250101_1200.qda")
        assert "2 backups: " in run(tmp_path)[1]

    @pytest.mark.parametrize("parts", [
        ("2025", "Interviews.qda"), ("2025", "spring", "Interviews.qda")])
    def test_projects_in_subfolders(self, tmp_path, parts):
        self._project(tmp_path, *parts)
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 0
        assert "holds 1 project, up to" in out
        assert quoted(os.path.join(*parts)) in out
        assert "may remove" not in out and "empty" not in out

    def test_deeper_still_it_is_not_empty(self, tmp_path):
        self._project(tmp_path, "a", "b", "c", "Deep.qda")
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 0
        assert ("holds no project within three folders of it, but it is "
                "not empty") in out
        assert 'at its top level' not in out and '"a"' in out
        assert "may remove" not in out

    def test_other_files_are_named_and_never_offered(self, tmp_path):
        folder = tmp_path.joinpath(*self.FOLDER)
        write(folder / "export.docx", "x")
        (folder / ".DS_Store").write_bytes(b"")
        code, out = run(tmp_path)
        assert code == 0
        assert '".DS_Store", "export.docx"' in out
        assert "may remove" not in out and "never removes a folder" in out

    def test_backups_are_named(self, tmp_path):
        self._project(tmp_path, "Study.qda")
        self._project(tmp_path, "old", "Study_backup_20250101_1200.qda")
        code, out = run(tmp_path)
        assert "1 backup: " + quoted(os.path.join(
            "old", "Study_backup_20250101_1200.qda")) in out

    def test_empty_it_is_yours_to_remove(self, tmp_path):
        folder = tmp_path.joinpath(*self.FOLDER)
        folder.mkdir(parents=True)
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 1 and "is empty" in out
        assert "may remove it yourself" in out
        assert "never removes a folder" in out
        assert folder.is_dir()


class TestTheProcessList:
    """Whether an older copy runs is read from ps, by its full path, on
    macOS and Linux and from Windows PowerShell on Windows, started by
    its full path in the system folder: a bare name is looked up on the
    PATH, or in the current folder first on Windows, so another program
    could be run. Without either nothing is read, so nothing is removed.
    The check itself and the programs that started it are left out."""

    OUT = b"1 0 uvx qualcoder-mcp\n"
    # PowerShell's lines also say when each program started
    OUT_WINDOWS = b"1 0 134000000000000000 uvx qualcoder-mcp\n"

    def _run(self, monkeypatch):
        calls = []

        def run(cmd, **kwargs):
            calls.append(list(cmd))
            out = self.OUT_WINDOWS if cmd[0].endswith(".exe") else self.OUT
            return subprocess.CompletedProcess(cmd, 0, out, b"")
        monkeypatch.setattr(transition.subprocess, "run", run)
        monkeypatch.setattr(transition, "_own_ids", lambda: (1000, 999))
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
        assert "ParentProcessId" in calls[0][3]
        assert "CreationDate" in calls[0][3]
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

    def test_ps_by_its_full_path(self, tmp_path, monkeypatch):
        ps = write(tmp_path / "bin" / "ps", "")
        monkeypatch.setattr(transition, "POSIX_PS",
                            (str(tmp_path / "missing"), str(ps)))
        calls = self._run(monkeypatch)
        assert self._listing_as(monkeypatch, "posix") == \
            ["uvx qualcoder-mcp"]
        assert calls == [[str(ps), "-axo", "pid=,ppid=,args="]]
        assert all(os.path.isabs(p) for p in transition.POSIX_PS)

    def test_without_ps_nothing_is_read(self, tmp_path, monkeypatch):
        monkeypatch.setattr(transition, "POSIX_PS",
                            (str(tmp_path / "missing"),))
        calls = self._run(monkeypatch)
        assert self._listing_as(monkeypatch, "posix") is None
        assert calls == []

    @POSIX_ONLY
    def test_a_ps_on_the_path_is_never_run(self, tmp_path, monkeypatch):
        fake = write(tmp_path / "bin" / "ps",
                     f"#!/bin/sh\ntouch {shlex.quote(str(tmp_path))}/ran\n"
                     "echo '1 0 nothing'\n")
        fake.chmod(0o755)
        monkeypatch.setenv("PATH", str(fake.parent) + os.pathsep +
                           os.environ.get("PATH", ""))
        lines = transition._listing()
        assert lines is not None and not (tmp_path / "ran").exists()

    def test_the_check_and_what_started_it_are_left_out(self, monkeypatch):
        # (id, parent's id, when it started or None, command line)
        rows = [(1000, 999, None, "/v/bin/python -m exegete.server "
                                  "--check-transition"),
                (999, 998, None, "/v/bin/uv tool uvx qualcoder-mcp"),
                (998, 997, None, "C:\\v\\Scripts\\qualcoder-mcp.exe --tidy"),
                (997, 1, None, "-zsh"),
                (1, 0, None, "/sbin/launchd"),
                (2000, 1, None, "/v/bin/python -m qualcoder_mcp.server")]
        monkeypatch.setattr(transition, "_process_table", lambda: rows)
        monkeypatch.setattr(transition, "_own_ids", lambda: (1000, 999))
        assert transition.started_as_old(transition._listing()) == \
            ["/v/bin/python -m qualcoder_mcp.server"]

    def test_naming_the_switch_hides_nothing(self, monkeypatch):
        # 0.10 and 0.11 ignore their arguments: `qualcoder-mcp
        # --check-transition` there starts a real server
        others = ["/w/bin/python /w/bin/qualcoder-mcp --check-transition",
                  "/x/my --check-transition dir/bin/qualcoder-mcp"]
        rows = [(1000, 999, None, "/v/bin/python -m exegete.server "
                                  "--check-transition"),
                (999, 1, None, "/v/bin/uvx qualcoder-mcp --check-transition"),
                (3000, 1, None, others[0]), (3001, 1, None, others[1])]
        monkeypatch.setattr(transition, "_process_table", lambda: rows)
        monkeypatch.setattr(transition, "_own_ids", lambda: (1000, 999))
        assert transition.started_as_old(transition._listing()) == others

    def test_a_reused_number_is_no_ancestor(self, monkeypatch):
        # Windows keeps a dead parent's number, which a later program can
        # take: an ancestor started before its child, never after
        rows = [(1000, 999, 500, "C:\\v\\python.exe -m exegete.server "
                                 "--check-transition"),
                (999, 998, 900, "C:\\w\\Scripts\\qualcoder-mcp.exe"),
                (998, 4, 100, "C:\\v\\Scripts\\qualcoder-mcp.exe"),
                (2000, 998, 400, "C:\\v\\Scripts\\uv.exe tool uvx "
                                 "qualcoder-mcp")]
        monkeypatch.setattr(transition, "_process_table", lambda: rows)
        monkeypatch.setattr(transition, "_own_ids", lambda: (1000, 999))
        assert transition.started_as_old(transition._listing()) == [
            "C:\\w\\Scripts\\qualcoder-mcp.exe",
            "C:\\v\\Scripts\\qualcoder-mcp.exe",
            "C:\\v\\Scripts\\uv.exe tool uvx qualcoder-mcp"]
        # started in the right order, the chain is the check's own
        rows[1] = (999, 998, 300, rows[1][3])
        assert transition.started_as_old(transition._listing()) == [
            "C:\\v\\Scripts\\uv.exe tool uvx qualcoder-mcp"]

    # A list that takes too long. Windows PowerShell's Get-CimInstance
    # once took more than the 20 seconds 0.14.1 allowed, on CI's Windows
    # runner; the check then keeps the link, and a researcher on a slow
    # computer could not tidy. 0.14.2 gives PowerShell longer and asks
    # once more after a time-out.

    def _slow(self, monkeypatch, tmp_path, os_name, times_out,
              error=subprocess.TimeoutExpired):
        """The list on `os_name`, from a subprocess.run that fails with
        `error` the first `times_out` times; returns the listing and the
        limit given to each call."""
        if os_name == "nt":
            root, _ = self._windows(tmp_path)
            monkeypatch.setenv("SystemRoot", str(root))
        else:
            ps = write(tmp_path / "bin" / "ps", "")
            monkeypatch.setattr(transition, "POSIX_PS", (str(ps),))
        limits = []

        def run(cmd, **kwargs):
            limits.append(kwargs.get("timeout"))
            if len(limits) <= times_out:
                if error is subprocess.TimeoutExpired:
                    raise error(cmd, kwargs.get("timeout"))
                raise error("cannot start it")
            out = self.OUT_WINDOWS if cmd[0].endswith(".exe") else self.OUT
            return subprocess.CompletedProcess(cmd, 0, out, b"")
        monkeypatch.setattr(transition.subprocess, "run", run)
        monkeypatch.setattr(transition, "_own_ids", lambda: (1000, 999))
        return self._listing_as(monkeypatch, os_name), limits

    @pytest.mark.parametrize("os_name", ["nt", "posix"])
    def test_a_slow_list_is_asked_for_once_more(self, tmp_path, monkeypatch,
                                               os_name):
        lines, limits = self._slow(monkeypatch, tmp_path, os_name, 1)
        assert lines == ["uvx qualcoder-mcp"]
        assert len(limits) == 2

    @pytest.mark.parametrize("os_name", ["nt", "posix"])
    def test_too_slow_twice_reads_nothing(self, tmp_path, monkeypatch,
                                          os_name):
        # nothing is read, so nothing is removed; and no third try
        lines, limits = self._slow(monkeypatch, tmp_path, os_name, 2)
        assert lines is None
        assert len(limits) == 2

    def test_another_failure_is_not_tried_again(self, tmp_path, monkeypatch):
        lines, limits = self._slow(monkeypatch, tmp_path, "nt", 1,
                                   error=OSError)
        assert lines is None
        assert len(limits) == 1

    def test_powershell_is_given_a_minute(self, tmp_path, monkeypatch):
        _, windows = self._slow(monkeypatch, tmp_path, "nt", 0)
        assert windows == [60]
        _, posix = self._slow(monkeypatch, tmp_path, "posix", 0)
        assert posix == [20]

    def test_the_real_process_list_holds_this_process(self, monkeypatch):
        # on Windows this runs the PowerShell command itself, so a mistake
        # in it shows here rather than as "could not be read". A CI runner
        # under load can be slower than any researcher's computer: the
        # test gives the same command more time than the check does, so a
        # slow runner does not fail it and what it proves is unchanged
        monkeypatch.setitem(transition.PROCESS_LIST_SECONDS, "windows", 150)
        monkeypatch.setitem(transition.PROCESS_LIST_SECONDS, "posix", 60)
        rows = transition._process_table()
        assert rows is not None
        mine = [row for row in rows if row[0] == os.getpid()]
        assert len(mine) == 1 and mine[0][1] == os.getppid()
        if os.name == "nt":
            assert mine[0][2]                       # when it started
            parent = [row for row in rows if row[0] == os.getppid()]
            assert not parent or parent[0][2] <= mine[0][2]
        else:
            assert mine[0][2] is None


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
                      "a folder", "exit code 0", "in its order",
                      "installing Exegete first", "uv tool or pipx",
                      "older than 0.14.1", "full paths"):
            assert words in flat, words
        overview = json.loads(server.explain_ai_coding_tools())
        assert "moving_from_qualcoder_mcp" in overview[
            "moving_from_qualcoder_mcp"]
        unknown = json.loads(server.explain_ai_coding_tools("nope"))
        assert "moving_from_qualcoder_mcp" in unknown["available_tools"]

    def test_it_says_what_holds_the_link(self):
        topic = json.loads(server.explain_ai_coding_tools(
            "moving_from_qualcoder_mcp"))
        check = " ".join(topic["the_check"].split())
        tidy = " ".join(topic["tidy"].split())
        assert "a desktop extension older than Exegete, to update" in check
        assert ("For a copy of the source it names the folder and says to "
                "quit the AI host before updating it") in check
        assert "or a desktop extension older than Exegete" in tidy
        assert ("cannot see an older copy started from a project's own "
                ".mcp.json file") in tidy

    def test_it_tells_desktop_extension_users_how_to_run_it(self):
        topic = json.loads(server.explain_ai_coding_tools(
            "moving_from_qualcoder_mcp"))
        extension = " ".join(topic["desktop_extension"].split())
        assert "`uvx exegete@latest --check-transition`" in extension
        assert "uvx exegete --check-transition" not in extension
        assert "installs no command" in extension
        assert "~/.qualcoder_mcp" in extension


def test_ci_follows_the_steps_with_the_real_installers():
    """The rename job's Linux entry runs the real uv tool and pipx through
    the check's steps, with pipx and a pip it accepts in the wheelhouse
    (pipx 1.17 asks for pip 26.1 or later)."""
    from test_v012_workflow_pins import WORKFLOWS, _jobs
    job = {j["name"]: "\n".join(j["lines"])
           for j in _jobs(WORKFLOWS / "ci.yml")}["rename-upgrade"]
    ubuntu = re.search(r"- os: ubuntu-latest\n\s+tests: (.+)", job)
    assert "tests/test_v0141_transition_installers.py" in \
        ubuntu.group(1).split()
    download = re.search(r'pip download --dest "\$RUNNER_TEMP/wheelhouse" '
                         r'--only-binary=:all: (.+)', job).group(1)
    assert re.search(r'"pipx(==[\d.]+)?"', download)
    assert '"pip>=26.1"' in download


def section(text, start, end):
    text = " ".join(text.split())
    part = text[text.index(start):]
    return part[:part.index(end)]


def test_the_documents_point_to_the_check():
    def flat(name):
        return " ".join((REPO / name).read_text(encoding="utf-8").split())
    install = section(flat("INSTALL.md"), "## Coming from qualcoder-mcp",
                      "## Upgrading from an earlier")
    assert "`exegete --check-transition`" in install
    assert "last release will say plainly that it is the last" in install
    unreleased = flat("CHANGELOG.md").split("## [0.14.0")[0]
    assert "exegete --check-transition" in unreleased
    assert "`--tidy`" in unreleased
    old = flat("packaging/pypi-old-name/README.md")
    assert "`exegete --check-transition`" in old
    assert "last release of this package will say plainly" in old


def test_the_documents_give_the_order_and_the_extensions_way():
    install = section((REPO / "INSTALL.md").read_text(encoding="utf-8"),
                      "## Coming from qualcoder-mcp",
                      "## Upgrading from an earlier")
    old = " ".join((REPO / "packaging" / "pypi-old-name" / "README.md")
                   .read_text(encoding="utf-8").split())
    for text in (install, old):
        assert "install `exegete` first" in text
        assert "then change" in text
    # v0.14.2: `@latest`, as the help topic says, since uv otherwise
    # reruns a copy it fetched before, whose check may not see the
    # extension
    assert "`uvx exegete@latest --check-transition`" in install
    assert "`uvx exegete --check-transition`" not in install
    assert "desktop extension" in install.split(
        "**Afterwards, the transition check.**")[1]
    assert "older than 0.14.1" in install
    assert "full paths" in install


def test_the_documents_say_what_holds_the_link():
    install = " ".join(section(
        (REPO / "INSTALL.md").read_text(encoding="utf-8"),
        "**Afterwards, the transition check.**",
        "## Upgrading from an earlier").split())
    unreleased = " ".join((REPO / "CHANGELOG.md").read_text(
        encoding="utf-8").split("## [0.14.0")[0].split())
    old = " ".join((REPO / "packaging" / "pypi-old-name" / "README.md")
                   .read_text(encoding="utf-8").split())
    for text in (install, unreleased, old):
        assert "desktop extension older than Exegete" in text
        assert "own `.mcp.json` file" in text
    for text in (install, unreleased):
        assert "names the folder and says to quit" in text


# ---------------------------------------------------------------------------
# 0.14.2: what the checks after 0.14.1 found
# ---------------------------------------------------------------------------

# Where Claude Desktop for Windows keeps its files when installed from its
# current installer, a Windows app package (MSIX): Windows keeps what the
# app writes under AppData\Roaming in the package's own folder.
PACKAGE = "Claude_pzs8sxrjxfjjc"


def packaged(home, package=PACKAGE):
    return home.joinpath("AppData", "Local", "Packages", package,
                         "LocalCache", "Roaming", "Claude")


class TestTheWindowsAppPackage:

    def test_an_older_extension_there_holds_the_link(self, tmp_path):
        TestTheLink()._moved(tmp_path)
        folder = packaged(tmp_path) / "Claude Extensions" / EXTENSION_ID
        write(folder / "manifest.json", json.dumps(
            {"name": "qualcoder-mcp", "version": "0.14.0-alpha"}))
        write(folder / "src" / "qualcoder_mcp" / "server.py", "")
        code, out = run(tmp_path, tidy=True)
        assert code == 1
        assert state_folder.is_link(tmp_path / ".qualcoder_mcp")
        assert "Done:" not in out
        shown = quoted("~" + os.sep + str(folder.relative_to(tmp_path)))
        assert (f"The desktop extension, qualcoder-mcp 0.14.0-alpha, in "
                f"{shown} is older than Exegete") in out

    def test_its_settings_file_is_read(self, tmp_path):
        config = write(packaged(tmp_path) / "claude_desktop_config.json",
                       json.dumps({"mcpServers": {"qualcoder": {
                           "command": "/v/bin/qualcoder-mcp"}}}))
        code, out = run(tmp_path)
        assert code == 1
        assert ("Claude Desktop's entry \"qualcoder\" still starts the old "
                "command.") in out
        assert quoted("~" + os.sep + str(config.relative_to(tmp_path))) \
            in out

    def test_its_old_logs_are_found(self, tmp_path):
        log = write(packaged(tmp_path) / "logs" /
                    "mcp-server-qualcoder-mcp.log", "log\n")
        code, out = run(tmp_path)
        assert code == 1 and "mcp-server-qualcoder-mcp.log" in out
        code, out = run(tmp_path, tidy=True, logs=True)
        assert code == 0, out
        assert not log.exists()

    def test_only_claudes_package_is_searched(self, tmp_path):
        for package in ("ClaudeHelper_x", "Other_x"):
            write(packaged(tmp_path, package) / "claude_desktop_config.json",
                  json.dumps({"mcpServers": {"qualcoder": {
                      "command": "/v/bin/qualcoder-mcp"}}}))
        code, out = run(tmp_path)
        assert code == 0, out
        assert transition.packaged_app_folders(tmp_path) == []
        write(packaged(tmp_path) / "x", "")
        assert transition.packaged_app_folders(tmp_path) == \
            [packaged(tmp_path)]


def uv_receipt(root, commands, inline=False):
    """The receipt uv tool writes beside a tool's environment: its
    requirements (none with an install path) and the commands it linked."""
    points = [f'{{ name = "{c}", install-path = "/h/.local/bin/{c}", '
              f'from = "{c}" }}' for c in commands]
    listed = ("entrypoints = [" + ", ".join(points) + "]" if inline else
              "entrypoints = [\n" + "".join(f"    {p},\n" for p in points) +
              "]")
    return write(root / "uv-receipt.toml",
                 '[tool]\nrequirements = [\n    { name = "qualcoder-mcp" },\n'
                 '    { name = "exegete" },\n]\n' + listed +
                 '\n\n[tool.options]\n')


class TestUvsExecutablesFrom:
    """`uv tool install qualcoder-mcp --with-executables-from exegete`
    links exegete's command from the old tool's environment and records
    it in that tool's receipt; `uv tool uninstall qualcoder-mcp` then
    removes it wherever it leads by then, Exegete's own install included
    (test_v0141_transition_installers.py runs the real uv)."""

    @pytest.mark.parametrize("py310", [False, True])
    @pytest.mark.parametrize("inline", [False, True])
    def test_what_the_receipt_says(self, tmp_path, monkeypatch, py310,
                                   inline):
        if py310:
            monkeypatch.setattr(transition, "tomllib", None)
        uv_receipt(tmp_path, ["exegete.exe", "qualcoder-mcp"], inline)
        assert transition.uv_tool_commands(tmp_path) == \
            ["exegete", "qualcoder-mcp"]
        uv_receipt(tmp_path, ["qualcoder-mcp"], inline)
        assert transition.uv_tool_commands(tmp_path) == ["qualcoder-mcp"]
        for text in ("[tool\n", "[" * 100000, ""):
            write(tmp_path / "uv-receipt.toml", text)
            assert transition.uv_tool_commands(tmp_path) == []
        (tmp_path / "uv-receipt.toml").unlink()
        assert transition.uv_tool_commands(tmp_path) == []

    @POSIX_ONLY
    def test_the_command_is_put_back_after_the_removal(self, tmp_path):
        home = tmp_path / "home"
        root = lay_out_tool(home, "uv tool", "qualcoder-mcp", "0.14.1a0",
                            inner_exegete=True)
        folder = home / ".local" / "bin"
        os.symlink(root / BIN / "exegete", folder / "exegete")
        uv_receipt(root, ["exegete", "qualcoder-mcp"])
        config = desktop_file(home, {"qualcoder": {
            "command": str(folder / "qualcoder-mcp")}})
        install = command_line(["uv", "tool", "install", "--force",
                                "exegete"])
        remove = command_line(["uv", "tool", "uninstall", "qualcoder-mcp"])
        code, out = run(home)
        assert pasted(out)[0] == install
        assert pasted(out)[-2:] == [remove, install]
        removal = items(out)[-1]
        flat = " ".join((removal[0] + " " + " ".join(removal[1])).split())
        assert "uv recorded the exegete command as one of its own" in flat
        assert "uv's uninstall removes the exegete command too" in flat
        # 1. Exegete installed, as uv does: a tool of its own, the command
        # linked into it
        (folder / "exegete").unlink()
        lay_out_tool(home, "uv tool", "exegete", "0.14.1a0")
        # 2. the entry, as printed
        code, out = run(home)
        entry = json.loads("{" + " ".join(
            line for line in pasted(out) if line.startswith('"')) + "}")
        config.write_text(json.dumps({"mcpServers": {"qualcoder": entry}}),
                          encoding="utf-8")
        code, out = run(home)
        assert pasted(out) == [remove, install]
        # 3. uv's uninstall: the old tool, and every command its receipt
        # names, although exegete's now leads into Exegete's own tool
        import shutil
        shutil.rmtree(root)
        for name in ("qualcoder-mcp", "exegete"):
            (folder / name).unlink()
        code, out = run(home)
        assert code == 1 and pasted(out) == [install]
        # then the step's second command, as uv does it
        os.symlink(home / TOOLS["uv tool"][0] / "exegete" / BIN / "exegete",
                   folder / "exegete")
        code, out = run(home)
        assert code == 0 and transition.NOTHING_LEFT in out

    def test_without_it_the_removal_is_as_before(self, tmp_path):
        home = tmp_path / "home"
        root = lay_out_tool(home, "uv tool", "qualcoder-mcp", "0.14.1a0",
                            inner_exegete=True)
        lay_out_tool(home, "uv tool", "exegete", "0.14.1a0")
        uv_receipt(root, ["qualcoder-mcp"])
        code, out = run(home)
        assert pasted(out) == [command_line(["uv", "tool", "uninstall",
                                             "qualcoder-mcp"])]


class TestAnEntryWhoseCommandIsGone:
    """A host's entry that starts the exegete command by a path where
    there is none: the host cannot start the server, so the check says
    so, rather than that nothing is left."""

    @pytest.mark.parametrize("kind", ["uv tool", "pipx"])
    def test_put_back_by_the_tool_that_installed_it(self, tmp_path, kind):
        home = tmp_path / "home"
        lay_out_tool(home, kind, "exegete", "0.14.1a0")
        command = home / ".local" / "bin" / "exegete"
        command.unlink()
        desktop_file(home, {"qualcoder": {"command": str(command)}})
        code, out = run(home)
        assert code == 1 and transition.NOTHING_LEFT not in out
        what, lines = items(out)[0]
        assert what == (f"Claude Desktop's entry \"qualcoder\" starts "
                        f"{quoted(str(command))}, which does not exist, so "
                        f"Claude Desktop cannot start Exegete.")
        assert "This comes first" in lines[0]
        assert pasted(out) == [command_line(
            TOOLS[kind][1] + ["install", "--force", "exegete"])]
        write(command, "#!/bin/sh\n")
        code, out = run(home)
        assert code == 0 and transition.NOTHING_LEFT in out

    def test_elsewhere_it_says_what_to_do(self, tmp_path):
        home = tmp_path / "home"
        command = home / "custom" / "exegete"
        write(home / ".codex" / "config.toml",
              f"[mcp_servers.qualcoder]\ncommand = {quoted(str(command))}\n")
        code, out = run(home)
        assert code == 1
        flat = " ".join(out.split())
        assert (f"Codex's entry \"qualcoder\" starts {quoted(str(command))}, "
                f"which does not exist") in flat
        assert ("Install Exegete so that this command exists (INSTALL.md), "
                "or change the entry \"qualcoder\"") in flat
        assert pasted(out) == []

    @pytest.mark.parametrize("entry", [
        {"command": "exegete"},                    # the host's own PATH
        {"command": "uvx", "args": ["exegete"]},
        {"command": "/v/bin/python", "args": ["-m", "exegete.server"]},
        {"command": "/v/bin/exegete-helper"},
    ])
    def test_only_a_path_to_the_command_is_judged(self, tmp_path, entry):
        desktop_file(tmp_path, {"qualcoder": entry})
        code, out = run(tmp_path)
        assert code == 0, out

    def test_a_home_relative_path_is_read_in_full(self, tmp_path):
        desktop_file(tmp_path, {"qualcoder": {
            "command": "~/.local/bin/exegete"}})
        code, out = run(tmp_path)
        assert quoted(str(tmp_path / ".local" / "bin" / "exegete")) in out
        write(tmp_path / ".local" / "bin" / "exegete", "")
        assert run(tmp_path)[0] == 0

    def test_said_once_while_exegete_is_to_be_installed(self, tmp_path):
        # the step that installs Exegete puts the command there
        home = tmp_path / "home"
        lay_out_tool(home, "uv tool", "qualcoder-mcp", "0.14.0a0")
        desktop_file(home, {"qualcoder": {
            "command": str(home / ".local" / "bin" / "exegete")}})
        code, out = run(home)
        assert "cannot start Exegete" not in out
        assert pasted(out)[0] == command_line(["uv", "tool", "install",
                                               "exegete"])


class TestPuttingTheLinkBack:
    """The tidy cannot see an older copy started from a project's own
    .mcp.json file, and says so in the step it carries out: once the link
    is removed, it also says how to put it back."""

    def test_the_tidy_says_how(self, tmp_path):
        TestTheLink()._moved(tmp_path)
        code, out = run(tmp_path, tidy=True)
        assert code == 0, out
        flat = " ".join(out.split())
        old, new = (quoted("~" + os.sep + name)
                    for name in (".qualcoder_mcp", ".exegete"))
        assert (f"Done: Removed the link {old}; {new} is untouched. Should "
                f"an older copy still start from a project's own .mcp.json "
                f"file, put the link back before it does.") in flat
        assert pasted(out) == [transition.put_back_link(tmp_path)]

    def test_not_said_while_the_link_stays(self, tmp_path):
        TestTheLink()._moved(tmp_path)
        code, out = run(tmp_path, tidy=True, lines=["uvx qualcoder-mcp"])
        assert "put the link back" not in out and pasted(out) == []
        code, out = run(tmp_path)
        assert "put the link back" not in out and pasted(out) == []

    @POSIX_ONLY
    def test_the_command_makes_the_link_the_move_made(self, tmp_path):
        new = TestTheLink()._moved(tmp_path)
        code, out = run(tmp_path, tidy=True)
        assert pasted(out) == [command_line(
            ["ln", "-s", ".exegete", str(tmp_path / ".qualcoder_mcp")])]
        done = subprocess.run(["/bin/sh", "-c", pasted(out)[0]],
                              capture_output=True, timeout=30)
        assert done.returncode == 0, done.stderr
        old = tmp_path / ".qualcoder_mcp"
        assert state_folder.is_link(old) and os.readlink(old) == ".exegete"
        assert state_folder.same_folder(old, new)
        assert "the link the move left" in run(tmp_path)[1]

    def test_on_windows_a_junction(self, tmp_path):
        assert transition.put_back_link(tmp_path, windows=True) == \
            command_line(["New-Item", "-ItemType", "Junction", "-Path",
                          str(tmp_path / ".qualcoder_mcp"), "-Target",
                          str(tmp_path / ".exegete")], windows=True)

    @pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell")
    def test_on_windows_the_command_makes_a_junction(self, tmp_path):
        new = TestTheLink()._moved(tmp_path)
        code, out = run(tmp_path, tidy=True)
        done = subprocess.run([transition.windows_powershell(), "-NoProfile",
                               "-Command", pasted(out)[0]],
                              capture_output=True, timeout=60)
        assert done.returncode == 0, done.stderr
        old = tmp_path / ".qualcoder_mcp"
        assert state_folder.is_link(old)
        assert state_folder.same_folder(old, new)


class TestBashOrZsh:
    """A command with a word written as $'...' (for characters that cannot
    be shown) is read by bash, zsh and the Mac's sh, and not by dash, the
    sh of Debian and Ubuntu: the check says where to paste it."""

    def test_what_counts(self):
        assert transition.needs_bash_or_zsh(
            [command_line(["/a b/python", "-m", "pip"], windows=False)])
        assert transition.needs_bash_or_zsh(
            ["git pull", command_line(["git", "-C", "/x​y", "pull"],
                                      windows=False)])
        assert not transition.needs_bash_or_zsh(
            [command_line(["/a b/it's $x", "-m", "pip"], windows=False),
             '"command": "/a $\'b",', "command = \"a $'b\""])

    @POSIX_ONLY
    def test_said_beside_such_a_command_alone(self, tmp_path):
        home = tmp_path / "home"
        env = env_with_old_package(home / "a venv")
        code, out = run(home, prefix=env)
        assert any(line.startswith("$'") for line in pasted(out))
        assert f"\n   {transition.BASH_OR_ZSH}\n" in out
        env = env_with_old_package(home / ODD)
        code, out = run(home, prefix=env)
        assert transition.BASH_OR_ZSH not in out

    @pytest.mark.skipif(not os.path.exists("/bin/dash"), reason="no dash")
    def test_dash_cannot_read_it(self):
        line = "printf %s " + command_line(["a b"], windows=False)
        got = {shell: subprocess.run([shell, "-c", line], capture_output=True,
                                     timeout=30).stdout
               for shell in ("/bin/bash", "/bin/dash")}
        assert got["/bin/bash"] == "a b".encode("utf-8")
        assert got["/bin/dash"] != "a b".encode("utf-8")


def test_the_help_topic_says_what_0_14_2_added():
    topic = json.loads(server.explain_ai_coding_tools(
        "moving_from_qualcoder_mcp"))
    check = " ".join(topic["the_check"].split())
    tidy = " ".join(topic["tidy"].split())
    extension = " ".join(topic["desktop_extension"].split())
    assert ("(or, where a host's entry starts an exegete command that is no "
            "longer there, the command that puts it back)") in check
    assert ("(once it has removed the link, it prints the command that puts "
            "it back)") in tidy
    assert ("(@latest makes uv fetch the newest release, rather than run "
            "one it fetched before, whose check may not know the "
            "extension)") in extension


def test_the_changelog_says_what_0_14_2_changed_in_the_check():
    changelog = " ".join((REPO / "CHANGELOG.md").read_text(
        encoding="utf-8").split())
    entry = changelog[changelog.index("### Fixed: the transition check"):
                      changelog.index("## [0.14.1-alpha]")]
    entry = entry[:entry.index("### ", 4)]
    for words in (
            "uv tool install qualcoder-mcp --with-executables-from exegete",
            "`uv tool install --force exegete`",
            "with the command that puts it back when uv or pipx installed",
            "Claude Desktop's app package",
            "prints the one command that puts it back",
            "paste it into bash or zsh",
            "is given 60 seconds instead of 20, and is asked for once more "
            "after a time-out",
            "`uvx exegete@latest --check-transition`"):
        assert words in entry, words
    assert transition.PROCESS_LIST_SECONDS == {"windows": 60, "posix": 20}
    assert transition.PROCESS_LIST_TRIES == 2
