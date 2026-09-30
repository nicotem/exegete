# SPDX-License-Identifier: LGPL-3.0-or-later
"""`exegete --check-transition`: what the move from qualcoder-mcp left.

The owner's rulings 42 and 43 (30 September 2026). Read-only by default:
it prints, plainly, what the change of name left behind on this computer
and the one step that tidies each, and exits 0 when nothing is left.

- the old `qualcoder-mcp` package still installed, and how it was
  installed (pip, uv, uv tool, pipx, a copy of the source), with the
  matching command to remove it;
- an entry in a host's configuration (Claude Desktop, Claude Code,
  LM Studio, Codex) that still starts the old command, with the entry to
  use instead (the files are only read, never changed);
- the link left at ~/.qualcoder_mcp, and whether it can safely go (it
  leads to ~/.exegete and no program started as qualcoder-mcp is
  running);
- Claude Desktop's log files under the extension's earlier name;
- the earlier default projects folder (its projects are still found;
  never moved or emptied: it is reported, and needs nothing).

`--tidy` removes only what this program owns and can show to be unused:
the link (never a folder), and the old log files only when
`--tidy-old-logs` is given as well. Everything else is a step printed
for the user. Projects, backups, the AI coder name files in projects and
every host's configuration are never touched. It never moves the state
folder and never makes one.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import env_settings, names, state_folder

try:
    import tomllib
except ModuleNotFoundError:                    # Python 3.10
    tomllib = None

# The larger host files (Claude Code's ~/.claude.json) can be several MB;
# anything past this is not read.
CONFIG_READ_MAX_BYTES = 32 * 1024 * 1024
OLD_LOG = re.compile(r"mcp-server-qualcoder-mcp\d*\.log")
_OLD_ARG = re.compile(r"(^|[\\/])qualcoder-mcp(\.exe)?$")


class Finding:
    """One thing the change left behind (or kept on purpose)."""

    def __init__(self, what: str, step: str, left: bool = True,
                 tidy: Optional[Callable[[], Tuple[bool, str]]] = None,
                 is_log: bool = False):
        self.is_log = is_log
        self.what, self.step, self.left, self.tidy = what, step, left, tidy


# ---------------------------------------------------------------------------
# Where things live, from the home folder alone (no environment is read)
# ---------------------------------------------------------------------------

# The folder Claude Desktop keeps its files and logs in: the app's name
# without its second word.
_APP_FOLDER = "Claude Desktop".split()[0]

def host_config_files(home: Path) -> List[Tuple[str, Path]]:
    appdata = home / "AppData" / "Roaming"
    return [
        ("Claude Desktop", home / "Library" / "Application Support" /
         _APP_FOLDER / "claude_desktop_config.json"),
        ("Claude Desktop", appdata / _APP_FOLDER /
         "claude_desktop_config.json"),
        ("Claude Desktop", home / ".config" / _APP_FOLDER /
         "claude_desktop_config.json"),
        ("Claude Code", home / ".claude.json"),
        ("LM Studio", home / ".lmstudio" / "mcp.json"),
        ("Codex", home / ".codex" / "config.toml"),
    ]


def claude_log_folders(home: Path) -> List[Path]:
    return [home / "Library" / "Logs" / _APP_FOLDER,
            home / "AppData" / "Roaming" / _APP_FOLDER / "logs",
            home / ".config" / _APP_FOLDER / "logs"]


def tool_folders(home: Path) -> List[Tuple[str, Path]]:
    """Where uv tool and pipx keep a tool's own environment by default."""
    return [
        ("uv tool", home / ".local" / "share" / "uv" / "tools"),
        ("uv tool", home / "AppData" / "Roaming" / "uv" / "data" / "tools"),
        ("pipx", home / ".local" / "pipx" / "venvs"),
        ("pipx", home / ".local" / "share" / "pipx" / "venvs"),
        ("pipx", home / "Library" / "Application Support" / "pipx" /
         "venvs"),
        ("pipx", home / "AppData" / "Local" / "pipx" / "pipx" / "venvs"),
    ]


# ---------------------------------------------------------------------------
# The old package
# ---------------------------------------------------------------------------

def _dist_info(env_root: Path) -> Optional[Path]:
    """The `qualcoder_mcp-*.dist-info` folder in an environment, if any."""
    for pattern in ("lib/python*/site-packages/qualcoder_mcp-*.dist-info",
                    "Lib/site-packages/qualcoder_mcp-*.dist-info"):
        for found in sorted(env_root.glob(pattern)):
            if found.is_dir():
                return found
    return None


def _python_of(env_root: Path) -> Path:
    windows = (env_root / "Scripts").is_dir()
    return (env_root / "Scripts" / "python.exe" if windows
            else env_root / "bin" / "python")


def _install_step(env_root: Path, dist_info: Path, home: Path) -> str:
    """The command that removes qualcoder-mcp, by how it was installed."""
    parts = [p.lower() for p in env_root.parts]
    if any(parts[i:i + 2] == ["uv", "tools"] or
           parts[i:i + 3] == ["uv", "data", "tools"]
           for i in range(len(parts))):
        return "uv tool uninstall qualcoder-mcp"
    if "pipx" in parts:
        return "pipx uninstall qualcoder-mcp"
    python = _python_of(env_root)
    try:
        installer = (dist_info / "INSTALLER").read_text(
            encoding="utf-8").strip()
    except OSError:
        installer = "pip"
    editable = False
    try:
        direct = json.loads((dist_info / "direct_url.json").read_text(
            encoding="utf-8"))
        editable = bool(direct.get("dir_info", {}).get("editable"))
    except (OSError, ValueError, AttributeError):
        pass
    if installer == "uv":
        step = f'uv pip uninstall --python "{python}" qualcoder-mcp'
    else:
        step = f'"{python}" -m pip uninstall qualcoder-mcp'
    if editable:
        step += (", then, in the folder of your copy of the source, "
                 f'"{python}" -m pip install -e .')
    return step


def old_package(home: Path, prefix: Optional[Path] = None,
                which: Callable[[str], Optional[str]] = shutil.which
                ) -> List[Finding]:
    """The old package, in this environment, behind the `qualcoder-mcp`
    command on the PATH, and in uv's and pipx's tool folders."""
    roots: List[Path] = [Path(sys.prefix if prefix is None else prefix)]
    command = which(names.OLD_COMMAND)
    if command:
        roots.append(Path(os.path.realpath(command)).parent.parent)
    for _, folder in tool_folders(home):
        roots.append(folder / names.OLD_DISTRIBUTION)
    findings, seen = [], set()
    for root in roots:
        try:
            key = os.path.normcase(os.path.realpath(root))
        except (OSError, ValueError):
            continue
        if key in seen:
            continue
        seen.add(key)
        info = _dist_info(root)
        if info is None:
            continue
        findings.append(Finding(
            f"The old package, qualcoder-mcp, is still installed in "
            f"{root}.",
            f"First change every host entry that starts qualcoder-mcp "
            f"(listed here, if any), then: "
            f"{_install_step(root, info, home)}"))
    return findings


# ---------------------------------------------------------------------------
# Host configurations (read only)
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Optional[dict]:
    try:
        if path.stat().st_size > CONFIG_READ_MAX_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _toml_servers(text: str) -> Dict[str, dict]:
    """Codex's [mcp_servers.NAME] tables: tomllib, or on Python 3.10 a
    reading of the `command` and `args` lines alone."""
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except (tomllib.TOMLDecodeError, ValueError):
            return {}
        servers = data.get("mcp_servers")
        return servers if isinstance(servers, dict) else {}
    servers: Dict[str, dict] = {}
    current = None
    for line in text.splitlines():
        head = re.match(r'\s*\[mcp_servers\.("?)([^"\]]+)\1\]\s*$', line)
        if head:
            current = servers.setdefault(head.group(2), {})
            continue
        if line.strip().startswith("["):
            current = None
            continue
        if current is None:
            continue
        pair = re.match(r'\s*(command|args)\s*=\s*(.+)$', line)
        if pair:
            try:
                current[pair.group(1)] = json.loads(pair.group(2))
            except ValueError:
                pass
    return servers


def _servers(label: str, path: Path) -> List[Tuple[str, dict]]:
    """(entry name, entry) for every MCP server entry in a host's file."""
    if label == "Codex":
        try:
            if path.stat().st_size > CONFIG_READ_MAX_BYTES:
                return []
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            return []
        return [(n, e) for n, e in _toml_servers(text).items()
                if isinstance(e, dict)]
    data = _read_json(path)
    if data is None:
        return []
    found: List[Tuple[str, dict]] = []
    tables = [data.get("mcpServers")]
    if label == "Claude Code":
        for project in (data.get("projects") or {}).values():
            if isinstance(project, dict):
                tables.append(project.get("mcpServers"))
    for table in tables:
        if isinstance(table, dict):
            found += [(n, e) for n, e in table.items()
                      if isinstance(e, dict)]
    return found


def _renamed(value: str) -> str:
    if value == "qualcoder_mcp.server":
        return "exegete.server"
    match = _OLD_ARG.search(value)
    if match:
        return value[:match.start()] + match.group(1) + names.COMMAND + \
            (match.group(2) or "")
    return value


def old_entry(entry: dict) -> Optional[Tuple[str, List[str]]]:
    """The entry to use instead, when this one starts the old command."""
    command = entry.get("command")
    args = entry.get("args") or []
    if not isinstance(command, str) or not isinstance(args, list) or \
            not all(isinstance(a, str) for a in args):
        return None
    new_args, previous = [], command
    for arg in args:
        # a folder named qualcoder-mcp (a clone, uv's --directory) keeps
        # its name: only the command and the module change
        folder = previous in _FOLDER_OPTIONS or os.path.isdir(arg)
        new_args.append(arg if folder else _renamed(arg))
        previous = arg
    new_command = _renamed(command)
    if new_command == command and new_args == args:
        return None
    return new_command, new_args


_FOLDER_OPTIONS = ("--directory", "--project", "--cwd", "-C")


def host_entries(home: Path) -> List[Finding]:
    findings = []
    for label, path in host_config_files(home):
        if not path.is_file():
            continue
        for name, entry in _servers(label, path):
            new = old_entry(entry)
            if new is None:
                continue
            command, args = new
            env = entry.get("env") if isinstance(entry.get("env"), dict) \
                else {}
            earlier = sorted(k for k in env if k.startswith(
                ("QUALCODER_MCP_", "QUALCODER_PROJECT_PATH")))
            step = (f"In {path}, change the entry \"{name}\" to start "
                    f"{json.dumps(command)} with the arguments "
                    f"{json.dumps(args)}; keep its name. Quit {label} "
                    f"first and reopen it afterwards.")
            if earlier:
                step += (" Its settings may keep their earlier spellings "
                         "until v1.0, or take the new ones: " + ", ".join(
                             f"{k} becomes {_new_spelling(k)}"
                             for k in earlier) + ".")
            findings.append(Finding(
                f"{label}'s entry \"{name}\" still starts the old command.",
                step))
    return findings


def _new_spelling(old: str) -> str:
    for new, earlier in names.SETTINGS.values():
        if earlier == old:
            return new
    return old


# ---------------------------------------------------------------------------
# Programs still started as qualcoder-mcp
# ---------------------------------------------------------------------------

def windows_powershell() -> Optional[str]:
    """Windows PowerShell's full path in the system folder, or None when
    it is not there. Never a bare name: Windows looks a bare name up in
    the current folder before the system folders, so a powershell.exe in
    the folder the check is run from would be run instead."""
    path = os.path.join(env_settings.windows_system_root(), "System32",
                        "WindowsPowerShell", "v1.0", "powershell.exe")
    return path if os.path.isfile(path) else None


def _listing() -> Optional[List[str]]:
    """Every other process's command line, or None when it cannot be
    read (then nothing is removed)."""
    if os.name == "nt":
        powershell = windows_powershell()
        if powershell is None:
            return None
        cmd = [powershell, "-NoProfile", "-Command",
               "Get-CimInstance Win32_Process | ForEach-Object "
               "{ \"$($_.ProcessId) $($_.CommandLine)\" }"]
    else:
        cmd = ["ps", "-axo", "pid=,args="]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=20,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    lines = []
    for row in done.stdout.decode("utf-8", errors="replace").splitlines():
        pid, _, args = row.strip().partition(" ")
        if pid.isdigit() and int(pid) == os.getpid():
            continue
        lines.append(args)
    return lines


def started_as_old(lines: Iterable[str]) -> List[str]:
    """The command lines that run the old command or module."""
    hits = []
    for line in lines:
        words = line.split()
        if any(_OLD_ARG.search(w.strip('"')) for w in words) or \
                "qualcoder_mcp.server" in words:
            hits.append(line[:200])
    return hits


# ---------------------------------------------------------------------------
# The state folder's link, the old logs and the old projects folder
# ---------------------------------------------------------------------------

def _remove_link(link: Path) -> Tuple[bool, str]:
    """Remove the link (a junction on Windows) and never what it leads to;
    refuse anything that is not a link to ~/.exegete by then."""
    new = link.with_name(names.STATE_FOLDER)
    if not state_folder.is_link(link) or \
            not state_folder.same_folder(link, new):
        return False, f"Left {link}: it is no longer a link to {new}."
    try:
        if os.name == "nt" and not os.path.islink(link):
            os.rmdir(link)                    # a junction: the link alone
        else:
            os.unlink(link)
    except OSError as error:
        return False, f"Could not remove {link} ({type(error).__name__})."
    return True, f"Removed the link {link}; {new} is untouched."


def state_link(home: Path, busy: Optional[List[str]]) -> List[Finding]:
    old = state_folder.old_path(home)
    new = state_folder.new_path(home)
    if not os.path.lexists(old):
        return []
    if not state_folder.is_link(old) and not os.path.lexists(new):
        return [Finding(
            f"{old} has not been moved to {new} yet.",
            "Start Exegete once through your AI host: its first start moves "
            "the folder whole and leaves a link under the old name. Then "
            "run the check again.")]
    if not state_folder.is_link(old):
        return [Finding(
            f"{old} is a folder of its own, beside {new}: an older copy of "
            f"the server (0.14 or earlier) made it, with a secret key of its "
            f"own, which Exegete does not use.",
            "Quit or update that older copy first. Keeping the folder changes "
            "nothing for Exegete; removing it removes that copy's secret, "
            "sessions and privacy run records, so it is yours to decide. "
            "This check never removes a folder.")]
    if not state_folder.same_folder(old, new) or not new.is_dir():
        return [Finding(
            f"{old} is a link that does not lead to {new}.",
            "See where it leads before removing it yourself; this check "
            "removes only a link to Exegete's own folder.")]
    if busy is None:
        return [Finding(
            f"{old} is the link the move left, leading to {new}.",
            "Whether a program started as qualcoder-mcp is still running "
            "could not be read, so the link stays; quit every AI host, "
            "then run the check again.")]
    if busy:
        return [Finding(
            f"{old} is the link the move left, leading to {new}; a program "
            f"started as qualcoder-mcp is running and may still use it.",
            "Quit it (and change its entry, above) first, then run "
            "`exegete --check-transition --tidy`.")]
    return [Finding(
        f"{old} is the link the move left, leading to {new}, and nothing "
        f"started as qualcoder-mcp is running.",
        "`exegete --check-transition --tidy` removes the link (only the "
        "link: the folder it leads to is untouched).",
        tidy=lambda: _remove_link(old))]


def old_logs(home: Path, busy: Optional[List[str]]) -> List[Finding]:
    findings = []
    for folder in claude_log_folders(home):
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        logs = [p for p in entries if OLD_LOG.fullmatch(p.name)
                and p.is_file() and not p.is_symlink()]
        if not logs:
            continue
        listed = ", ".join(p.name for p in logs)
        if busy is None or busy:
            step = ("They may still be written while a program started as "
                    "qualcoder-mcp runs; quit it and run the check again.")
            tidy = None
        else:
            step = ("Claude Desktop no longer writes them (the extension "
                    "logs as Exegete). `exegete --check-transition --tidy "
                    "--tidy-old-logs` removes them; they are only logs.")
            tidy = (lambda logs=logs: _remove_logs(logs))
        findings.append(Finding(
            f"Claude Desktop's logs under the extension's earlier name, in "
            f"{folder}: {listed}.", step, tidy=tidy, is_log=True))
    return findings


def _remove_logs(logs: List[Path]) -> Tuple[bool, str]:
    removed = []
    for path in logs:
        try:
            if OLD_LOG.fullmatch(path.name) and path.is_file() and \
                    not path.is_symlink():
                path.unlink()
                removed.append(path.name)
        except OSError:
            continue
    return (len(removed) == len(logs),
            f"Removed the old logs: {', '.join(removed) or 'none'}.")


def old_projects_folder(home: Path) -> List[Finding]:
    folder = home / "Documents" / names.OLD_WORKSPACE_FOLDER
    try:
        with os.scandir(folder) as entries:
            projects = [e.name for e in entries
                        if e.name.lower().endswith(".qda")]
    except OSError:
        return []
    if projects:
        return [Finding(
            f"{folder}, the earlier projects folder, holds "
            f"{len(projects)} project(s).",
            "Nothing to do: Exegete never moves or empties it, and "
            "list_available_projects still finds them. To keep working "
            "there, set EXEGETE_WORKSPACE to it.", left=False)]
    return [Finding(
        f"{folder}, the earlier projects folder, is empty of projects.",
        "You may remove it yourself if you no longer want it; this check "
        "never removes a folder.")]


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------

HEADING = "Moving from qualcoder-mcp to Exegete: what the change left behind"
NOTHING_LEFT = ("Nothing is left behind: the move from qualcoder-mcp to "
                "Exegete is complete on this computer.")


def check(home: Optional[Path] = None, prefix: Optional[Path] = None,
          which: Callable[[str], Optional[str]] = shutil.which,
          listing: Callable[[], Optional[List[str]]] = _listing
          ) -> List[Finding]:
    """Everything, read-only."""
    home = Path.home() if home is None else Path(home)
    lines = listing()
    busy = None if lines is None else started_as_old(lines)
    return (old_package(home, prefix, which) + host_entries(home) +
            state_link(home, busy) + old_logs(home, busy) +
            old_projects_folder(home))


def run(tidy: bool = False, tidy_old_logs: bool = False,
        out=None, **where) -> int:
    """Print the check (and, with `tidy`, what it removed); the exit code
    is 0 when nothing is left behind, else 1."""
    out = sys.stdout if out is None else out
    findings = check(**where)
    home = str(Path.home() if where.get("home") is None else where["home"])

    def shown(text: str) -> str:
        """Paths in the home folder as ~/..., as the documents write them."""
        return text.replace(home + os.sep, "~" + os.sep)

    print(HEADING, file=out)
    print("", file=out)
    if not any(f.left for f in findings):
        print(NOTHING_LEFT, file=out)
    left = 0
    for number, finding in enumerate(findings, 1):
        print(f"{number}. {shown(finding.what)}", file=out)
        print(f"   What to do: {shown(finding.step)}", file=out)
        if tidy and finding.tidy is not None and \
                (tidy_old_logs or not finding.is_log):
            done, text = finding.tidy()
            print(f"   {'Done' if done else 'Not done'}: {shown(text)}",
                  file=out)
            if done:
                continue
        if finding.left:
            left += 1
    print("", file=out)
    print("Read-only unless --tidy was given; projects, backups and hosts' "
          "configuration files are never changed.", file=out)
    return 0 if left == 0 else 1
