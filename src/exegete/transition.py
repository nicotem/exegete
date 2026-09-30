# SPDX-License-Identifier: LGPL-3.0-or-later
"""`exegete --check-transition`: what the move from qualcoder-mcp left.

Read-only by default: it prints, plainly, what the change of name left
behind on this computer and the steps that tidy it, numbered in the
order to take them, and exits 0 when nothing is left.

- Exegete itself, first, when the old `qualcoder-mcp` package lives in
  an environment with no `exegete` command yet (a uv tool or pipx
  environment, or one holding 0.14.0 or earlier): a host's entry is
  never pointed at a command that does not exist, and the old package
  is never removed while an entry still needs it;
- an entry in a host's configuration (Claude Desktop, Claude Code,
  LM Studio, Codex) that still starts the old command, with the entry
  to use instead (the files are only read, never changed);
- the old package, with the command that removes it for the way it
  was installed (pip, uv, uv tool, pipx, a copy of the source);
- the link left at ~/.qualcoder_mcp, and whether it can safely go: it
  leads to ~/.exegete, no program started as qualcoder-mcp is running,
  and neither a qualcoder-mcp older than 0.14.1 nor a host entry that
  starts the old command is left;
- Claude Desktop's log files under the extension's earlier name;
- the earlier default projects folder, searched as the project listing
  searches (three levels down); never moved or emptied, and never
  offered for removal while anything is in it.

What the researcher pastes (commands, entries) carries full paths,
quoted for the shell or the file it goes into; `~` shortens paths in
prose only. Names and paths read from files and folders are shown as
JSON strings, so that none can break or disguise a line of the report.

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
import shlex
import shutil
import subprocess
import sys
import urllib.parse
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
# The old command as a word or at the end of a path, bare or pinned
# (`qualcoder-mcp==0.14.0`, `qualcoder-mcp@0.14.0`, with extras or not).
_OLD_ARG = re.compile(r"(^|[\\/])qualcoder-mcp(\.exe)?(?:\[[^\]]*\])?"
                      r"(?:(?:===|==|~=|!=|>=|<=|<|>|@)\S*)?$", re.I)
_OLD_MODULE = "qualcoder_mcp.server"
_NEW_MODULE = "exegete.server"
# From this release on, the old name's package only points to Exegete:
# its command runs Exegete, which never uses the link.
POINTER_SINCE = (0, 14, 1)
# The project listing's depth: a project up to three levels down.
PROJECT_DEPTH = 3
SHOWN_MAX = 10


class Finding:
    """One thing the change left behind (or kept on purpose): what it
    is, what to do, the commands or entry lines to paste (each printed
    on a line of its own), and what follows them."""

    def __init__(self, what: str, step: str, left: bool = True,
                 tidy: Optional[Callable[[], Tuple[bool, str]]] = None,
                 is_log: bool = False, commands: Iterable[str] = (),
                 after: str = ""):
        self.is_log = is_log
        self.what, self.step, self.left, self.tidy = what, step, left, tidy
        self.commands, self.after = list(commands), after


# ---------------------------------------------------------------------------
# Showing names and paths, and writing commands to paste
# ---------------------------------------------------------------------------

def _escape(char: str, toml: bool = False) -> str:
    code = ord(char)
    if code <= 0xFFFF:
        return "\\u%04x" % code
    if toml:
        return "\\U%08x" % code
    code -= 0x10000
    return "\\u%04x\\u%04x" % (0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF))


def quoted(text: str, toml: bool = False) -> str:
    """`text` as a JSON string (a TOML one with `toml`) with every
    character that is not printable escaped (line breaks, terminal
    controls, direction marks): a name read from a file or a folder can
    then never break a line of the report or disguise itself."""
    body = json.dumps(str(text), ensure_ascii=False)
    return "".join(c if c.isprintable() else _escape(c, toml) for c in body)


def _place(path, home: Path) -> str:
    """A path for prose: in the home folder as ~/..., quoted."""
    text, base = str(path), str(home).rstrip("\\/")
    if base and text == base:
        text = "~"
    elif base and text.startswith(base + os.sep):
        text = "~" + text[len(base):]
    return quoted(text)


def _utf8(char: str) -> bytes:
    """A character's bytes: UTF-8, or the byte itself for one the file
    system gave that was not UTF-8 (Python keeps it as a lone
    surrogate)."""
    try:
        return char.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError:
        return char.encode("utf-8", "surrogatepass")


def _sh_word(word: str) -> str:
    """One word for sh, bash or zsh: shlex's quoting, or ANSI-C quoting
    for a word with characters that cannot be shown as they are, written
    as their bytes (the Mac's bash 3.2 and sh read \\x, not \\u or
    \\U)."""
    if word.isprintable():
        return shlex.quote(word)
    out = []
    for c in word:
        if c in "\\'":
            out.append("\\" + c)
        elif c.isprintable():
            out.append(c)
        else:
            out.extend("\\x%02x" % byte for byte in _utf8(c))
    return "$'" + "".join(out) + "'"


_PS_PLAIN = re.compile(r"[A-Za-z0-9_./:\\=+-]+")
_PS_SINGLE = "'‘’‚‛"     # PowerShell reads all as '
_PS_DOUBLE = '"“”„'


def _ps_word(word: str) -> str:
    """One word for PowerShell: single quotes (every kind PowerShell
    reads as one doubled), or double quotes with escapes for a word
    with characters that cannot be shown as they are."""
    if _PS_PLAIN.fullmatch(word):
        return word
    if word.isprintable():
        return "'" + "".join(c * 2 if c in _PS_SINGLE else c
                             for c in word) + "'"
    out = []
    for c in word:
        if c in "`$" + _PS_DOUBLE:
            out.append("`" + c)
        elif c.isprintable():
            out.append(c)
        else:
            out.append("$([char]::ConvertFromUtf32(0x%x))" % ord(c))
    return '"' + "".join(out) + '"'


def command_line(argv: List[str], windows: Optional[bool] = None) -> str:
    """A command to paste, with full paths: for PowerShell on Windows
    (where a quoted program needs `&` in front), else for sh, bash and
    zsh."""
    windows = os.name == "nt" if windows is None else windows
    if not windows:
        return " ".join(_sh_word(word) for word in argv)
    words = [_ps_word(word) for word in argv]
    return ("& " if words[0] != argv[0] else "") + " ".join(words)


def _shell(windows: Optional[bool] = None) -> str:
    windows = os.name == "nt" if windows is None else windows
    return "In PowerShell" if windows else "In a terminal"


def _count(number: int, thing: str) -> str:
    """"1 project", "2 projects"."""
    return f"{number} {thing}" + ("" if number == 1 else "s")


def _listed(items: List[str]) -> str:
    shown = ", ".join(quoted(item) for item in items[:SHOWN_MAX])
    more = len(items) - SHOWN_MAX
    return shown + (f" and {more} more" if more > 0 else "")


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


# The folder the desktop app unpacks its extensions into, one each.
_EXTENSIONS = _APP_FOLDER + " Extensions"


def extension_folders(home: Path) -> List[Path]:
    return [home / "Library" / "Application Support" / _APP_FOLDER /
            _EXTENSIONS,
            home / "AppData" / "Roaming" / _APP_FOLDER / _EXTENSIONS,
            home / ".config" / _APP_FOLDER / _EXTENSIONS]


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


def tool_command_folder(home: Path) -> Path:
    """Where uv tool and pipx put a tool's commands by default."""
    return home / ".local" / "bin"


# ---------------------------------------------------------------------------
# The old package, wherever it is installed
# ---------------------------------------------------------------------------

def _dist_info(env_root: Path, dist: str = "qualcoder_mcp") -> Optional[Path]:
    """The `<dist>-*.dist-info` folder in an environment, if any."""
    for pattern in (f"lib/python*/site-packages/{dist}-*.dist-info",
                    f"Lib/site-packages/{dist}-*.dist-info"):
        try:
            for found in sorted(env_root.glob(pattern)):
                if found.is_dir():
                    return found
        except (OSError, ValueError):
            return None
    return None


def _python_of(env_root: Path) -> Path:
    windows = (env_root / "Scripts").is_dir()
    return (env_root / "Scripts" / "python.exe" if windows
            else env_root / "bin" / "python")


def _tool_kind(env_root: Path) -> Optional[str]:
    parts = [p.lower() for p in env_root.parts]
    if any(parts[i:i + 2] == ["uv", "tools"] or
           parts[i:i + 3] == ["uv", "data", "tools"]
           for i in range(len(parts))):
        return "uv tool"
    if "pipx" in parts:
        return "pipx"
    return None


def is_pointer(version: str) -> bool:
    """Whether this version of the old name's package only points to
    Exegete (0.14.1 on); anything unreadable counts as older."""
    match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version)
    if match is None:
        return False
    release = (int(match[1]), int(match[2]), int(match[3] or 0))
    return release >= POINTER_SINCE


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except (OSError, ValueError):
        return False


def _command_at(path: Path) -> bool:
    """Whether a command exists at `path` (with `.exe` on Windows)."""
    return _is_file(path) or (os.name == "nt" and
                              _is_file(path.with_name(path.name + ".exe")))


def _url_folder(url) -> Optional[Path]:
    """The folder a local file:// address names, when it is one."""
    if not isinstance(url, str):
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
        return None
    path = urllib.parse.unquote(parsed.path)
    if os.name == "nt" and re.match(r"/[A-Za-z]:", path):
        path = path[1:]                           # file:///C:/...
    try:
        return Path(path) if path and os.path.isdir(path) else None
    except (OSError, ValueError):
        return None


def _inside(path: str, root: Path) -> bool:
    try:
        real = Path(os.path.realpath(path))
        top = Path(os.path.realpath(root))
    except (OSError, ValueError):
        return False
    return real == top or top in real.parents


class OldInstall:
    """The old package in one environment, and how it was installed."""

    def __init__(self, root: Path, info: Path, home: Path):
        self.root, self.info = root, info
        self.version = info.name[:-len(".dist-info")].partition("-")[2]
        self.pointer = is_pointer(self.version)
        self.tool = _tool_kind(root)
        self.python = _python_of(root)
        try:
            self.installer = (info / "INSTALLER").read_text(
                encoding="utf-8").strip()
        except (OSError, ValueError):
            self.installer = "pip"
        self.editable = False
        # an editable install's copy of the source: where pip says it
        # installed from, or else the folder the environment is in
        self.source: Optional[Path] = None
        try:
            direct = json.loads((info / "direct_url.json").read_text(
                encoding="utf-8"))
            self.editable = bool(direct.get("dir_info", {}).get("editable"))
            if self.editable:
                self.source = _url_folder(direct.get("url"))
        except Exception:                        # a malformed file: no
            pass
        if self.editable and self.source is None and \
                _is_file(root.parent / "pyproject.toml"):
            self.source = root.parent
        # folders where the old command is linked from this environment
        self.command_folders: List[Path] = []
        self.needs_exegete = False
        # an exegete command that leads into this tool's environment
        # (pipx's --include-deps, inject): installing Exegete replaces it
        self.replace_command: Optional[str] = None

    def pip(self, *args: str) -> List[str]:
        if self.installer == "uv":
            return ["uv", "pip", args[0], "--python", str(self.python),
                    *args[1:]]
        return [str(self.python), "-m", "pip", *args]


# ---------------------------------------------------------------------------
# Host configurations (read only)
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> Optional[str]:
    try:
        if path.stat().st_size > CONFIG_READ_MAX_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig")
    except (OSError, ValueError):
        return None


def _read_json(path: Path) -> Optional[dict]:
    text = _read_text(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except Exception:
        # The whole class, as project_settings reads its file: a deeply
        # nested file makes CPython's parser raise RecursionError, which
        # is not a ValueError, and a host's file is not ours to trust.
        return None
    return data if isinstance(data, dict) else None


def _toml_servers(text: str) -> Dict[str, dict]:
    """Codex's [mcp_servers.NAME] tables: tomllib, or on Python 3.10 a
    reading of the `command` and `args` lines alone."""
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except Exception:                     # RecursionError too
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
            except Exception:
                pass
    return servers


def _servers(label: str, path: Path) -> List[Tuple[str, dict]]:
    """(entry name, entry) for every MCP server entry in a host's file;
    none when the file cannot be read or is not shaped as expected."""
    if label == "Codex":
        text = _read_text(path)
        if text is None:
            return []
        return [(str(n), e) for n, e in _toml_servers(text).items()
                if isinstance(e, dict)]
    data = _read_json(path)
    if data is None:
        return []
    tables = [data.get("mcpServers")]
    projects = data.get("projects")
    if label == "Claude Code" and isinstance(projects, dict):
        tables += [project.get("mcpServers") for project in projects.values()
                   if isinstance(project, dict)]
    found: List[Tuple[str, dict]] = []
    for table in tables:
        if isinstance(table, dict):
            found += [(str(n), e) for n, e in table.items()
                      if isinstance(e, dict)]
    return found


def _renamed(value: str) -> str:
    """The old command or module renamed; a pin to an old version goes
    (Exegete's first release is 0.14.1)."""
    if value == _OLD_MODULE:
        return _NEW_MODULE
    match = _OLD_ARG.search(value)
    if match:
        return value[:match.start()] + match.group(1) + names.COMMAND + \
            (match.group(2) or "")
    return value


_FOLDER_OPTIONS = ("--directory", "--project", "--cwd", "-C")


def _is_folder(path: str) -> bool:
    try:
        return os.path.isdir(path)
    except (OSError, ValueError):
        return False


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
        folder = previous in _FOLDER_OPTIONS or _is_folder(arg)
        new_args.append(arg if folder else _renamed(arg))
        previous = arg
    new_command = _renamed(command)
    if new_command == command and new_args == args:
        return None
    return new_command, new_args


class OldEntry:
    """A host's entry that still starts the old command."""

    def __init__(self, label: str, path: Path, name: str, entry: dict,
                 command: str, args: List[str]):
        self.label, self.path, self.name = label, path, name
        self.old_command = entry["command"]
        self.old_args = list(entry.get("args") or [])
        self.command, self.args = command, args
        env = entry.get("env") if isinstance(entry.get("env"), dict) else {}
        self.earlier = sorted(str(k) for k in env if str(k).startswith(
            ("QUALCODER_MCP_", "QUALCODER_PROJECT_PATH")))


def old_entries(home: Path) -> List[OldEntry]:
    found = []
    for label, path in host_config_files(home):
        if not _is_file(path):
            continue
        for name, entry in _servers(label, path):
            new = old_entry(entry)
            if new is not None:
                found.append(OldEntry(label, path, name, entry, *new))
    return found


def _as_path(command: str, home: Path) -> Optional[str]:
    """A command given as a path, in full (`~` read as the home folder,
    as a host that expands it would); None for a bare name."""
    if command[:2] in ("~/", "~\\"):
        return str(home / command[2:])
    rooted = os.path.isabs(command) or command.startswith(("/", "\\"))
    return command if rooted else None


def _word(text: str) -> str:
    """A short value read from a file (a version, a setting's name) as it
    is when plain, else quoted."""
    return text if re.fullmatch(r"[A-Za-z0-9_.+!-]+", text) else quoted(text)


# ---------------------------------------------------------------------------
# The old package: install Exegete first, change the entries, remove it
# ---------------------------------------------------------------------------

def old_installs(home: Path, prefix: Optional[Path] = None,
                 which: Callable[[str], Optional[str]] = shutil.which,
                 entries: Iterable[OldEntry] = ()) -> List[OldInstall]:
    """The old package in this environment, behind the old command on the
    PATH or in a host's entry, and in uv's and pipx's tool folders."""
    roots: List[Path] = [Path(sys.prefix if prefix is None else prefix)]
    commands: List[str] = []
    found = which(names.OLD_COMMAND)
    if found:
        commands.append(found)
    for entry in entries:
        path = _as_path(entry.old_command, home)
        if path is not None:
            commands.append(path)
    for command in commands:
        roots.append(Path(command).parent.parent)
        try:
            roots.append(Path(os.path.realpath(command)).parent.parent)
        except (OSError, ValueError):
            pass
    for _, folder in tool_folders(home):
        roots.append(folder / names.OLD_DISTRIBUTION)
    installs, seen = [], set()
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
        install = OldInstall(root, info, home)
        if install.tool:
            # the old command linked from outside the tool's environment
            install.command_folders = [
                Path(c).parent for c in commands
                if _inside(c, root) and not _inside(str(Path(c).parent),
                                                    root)]
            folders = install.command_folders + [tool_command_folder(home)]
            present = [str(f / names.COMMAND) for f in folders
                       if _command_at(f / names.COMMAND)]
            install.needs_exegete = not (
                any(_dist_info(tools / names.DISTRIBUTION, "exegete")
                    for _, tools in tool_folders(home)) or
                any(_stays(command, [install]) for command in present))
            if install.needs_exegete and present:
                install.replace_command = present[0]
        else:
            install.needs_exegete = _dist_info(root, "exegete") is None
        installs.append(install)
    return installs


def _stays(command: str, installs: Iterable[OldInstall]) -> bool:
    """Whether a command is there and stays once the old package goes: not
    one that leads into an old tool's own environment (pipx's
    --include-deps and inject link exegete's command from there, and
    removing the old package removes it)."""
    return _command_at(Path(command)) and not any(
        i.tool and _inside(command, i.root) for i in installs)


def _install_finding(install: OldInstall, home: Path) -> Finding:
    place, version = _place(install.root, home), _word(install.version)
    if install.tool:
        force = ["--force"] if install.replace_command else []
        argv = (["uv", "tool", "install", *force, names.DISTRIBUTION]
                if install.tool == "uv tool"
                else ["pipx", "install", *force, names.DISTRIBUTION])
        why = (f"{install.tool} puts only a package's own commands on the "
               f"PATH, so there is no exegete command yet"
               if not force else
               f"the exegete command at {quoted(install.replace_command)} "
               f"leads into the old package's own environment, so "
               f"removing the old package would take it too")
        return Finding(
            f"The old package, qualcoder-mcp {version}, is installed with "
            f"{install.tool}, in {place}, and Exegete is not: {why}.",
            f"This comes first. {_shell()}:",
            commands=[command_line(argv)],
            after="It installs the exegete command that the steps below "
                  "point your hosts at" + (
                      " (--force lets it replace the one there now)"
                      if force else "") +
                  ". Until it has, change nothing else: removing the old "
                  "package first would leave no server.")
    if install.editable:
        quit_first = ("This comes first. Quit your AI host first, since a "
                      "copy of the server left running fails when its files "
                      "change; then update your copy of the source")
        if install.source is None:
            return Finding(
                f"{place} has the old package, qualcoder-mcp {version}, "
                f"installed from a copy of the source, and not Exegete.",
                f"{quit_first}. {_shell()}, in its folder:",
                commands=["git pull",
                          command_line(install.pip("install", "-e", "."))])
        source = str(install.source)
        return Finding(
            f"{place} has the old package, qualcoder-mcp {version}, "
            f"installed from a copy of the source in "
            f"{_place(source, home)}, and not Exegete.",
            f"{quit_first} in {_place(source, home)}. {_shell()}:",
            commands=[command_line(["git", "-C", source, "pull"]),
                      command_line(install.pip("install", "-e", source))])
    return Finding(
        f"{place} has the old package, qualcoder-mcp {version}, and not "
        f"Exegete.",
        f"This comes first. {_shell()}:",
        commands=[command_line(install.pip("install", names.DISTRIBUTION))],
        after="It installs Exegete in that environment, beside the old "
              "package, which keeps working meanwhile.")


def _removal_finding(install: OldInstall, home: Path) -> Finding:
    if install.tool == "uv tool":
        commands = [command_line(["uv", "tool", "uninstall",
                                  names.OLD_DISTRIBUTION])]
    elif install.tool == "pipx":
        commands = [command_line(["pipx", "uninstall",
                                  names.OLD_DISTRIBUTION])]
    else:
        commands = [command_line(install.pip("uninstall",
                                             names.OLD_DISTRIBUTION))]
        if install.editable:
            commands.append(command_line(install.pip(
                "install", "-e", str(install.source or "."))))
    where = (f"{_shell()}, in the folder of your copy of the source:"
             if install.editable and not install.tool and
             install.source is None else f"{_shell()}:")
    return Finding(
        f"The old package, qualcoder-mcp {_word(install.version)}, is still "
        f"installed in {_place(install.root, home)}.",
        f"Once no host entry starts it any more (the steps above), remove "
        f"it. {where}",
        commands=commands)


def _same_root(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(os.path.realpath(a)) == \
            os.path.normcase(os.path.realpath(b))
    except (OSError, ValueError):
        return False


def _provides(install: OldInstall, old_command: str, home: Path) -> bool:
    """Whether installing Exegete for `install` puts the new command
    beside `old_command`: the old command is in its environment, or it is
    a tool's and sits where the tool's commands go (on Windows uv copies
    them there rather than linking them)."""
    if _inside(old_command, install.root):
        return True
    folder = Path(old_command).parent
    return bool(install.tool) and any(
        _same_root(folder, f) for f in
        install.command_folders + [tool_command_folder(home)])


def _readiness(entry: OldEntry, home: Path,
               which: Callable[[str], Optional[str]],
               installs: List[OldInstall]) -> str:
    """'' when the entry's new command is at hand (or cannot be judged
    from here), else what has to come first."""
    after_install = ("Make this change only after the step above that "
                     "installs Exegete: until then ")
    keep = ("or leave this entry as it is for now (the old way of "
            "starting keeps working until v1.0).")
    if entry.command != entry.old_command:
        new = _as_path(entry.command, home)
        old = _as_path(entry.old_command, home)
        if new is None:
            old = which(entry.old_command)
            there = [which(entry.command) or ""] + (
                [str(Path(old).parent / entry.command)] if old else [])
        else:
            there = [new]
        there = [c for c in there if c and _command_at(Path(c))]
        if any(_stays(c, installs) for c in there):
            return ""
        if old and any(i.needs_exegete and _provides(i, old, home)
                       for i in installs):
            return after_install + (
                f"{quoted(there[0])} leads into the old package's "
                f"environment, which goes when the old package is removed."
                if there else f"{quoted(entry.command)} does not exist.")
        return (f"{quoted(entry.command)} does not exist yet: install "
                f"Exegete where the old command is installed first, {keep}")
    if _NEW_MODULE in entry.args:
        python = _as_path(entry.command, home) or which(entry.command)
        if python is None:
            return ""
        root = Path(python).parent.parent
        if _dist_info(root, "exegete") is not None:
            return ""
        if any(i.needs_exegete and _same_root(i.root, root)
               for i in installs):
            return after_install + (f"the Python it starts, {quoted(python)},"
                                    f" has no Exegete yet.")
        install = command_line([python, "-m", "pip", "install",
                                names.DISTRIBUTION])
        return (f"The Python it starts has no Exegete yet: install it "
                f"there first ({_shell()}: {install}), {keep}")
    for option, value in zip(entry.args, entry.args[1:]):
        if option in ("--directory", "--project"):
            folder = Path(_as_path(value, home) or value)
            if not _is_file(folder / "src" / "exegete" / "server.py"):
                return (f"The copy of the source in {_place(value, home)} "
                        f"has no Exegete yet: update it first (git pull in "
                        f"that folder), {keep}")
    return ""


def _entry_finding(entry: OldEntry, home: Path,
                   which: Callable[[str], Optional[str]],
                   installs: List[OldInstall]) -> Finding:
    toml = entry.label == "Codex"
    command = quoted(entry.command, toml)
    args = "[" + ", ".join(quoted(a, toml) for a in entry.args) + "]"
    lines = ([f"command = {command}", f"args = {args}"] if toml else
             [f'"command": {command},', f'"args": {args}'])
    first = _readiness(entry, home, which, installs)
    after = (f"Keep the rest of the entry as it is, save the file and "
             f"reopen {entry.label}.")
    known = [(k, _new_spelling(k)) for k in entry.earlier
             if _new_spelling(k) is not None]
    if known:
        after += (" Its settings may keep their earlier spellings until "
                  "v1.0, or take the new ones: " + ", ".join(
                      f"{k} becomes {n}" for k, n in known) + ".")
    return Finding(
        f"{entry.label}'s entry {quoted(entry.name)} still starts the old "
        f"command.",
        (first + " " if first else "") +
        f"Quit {entry.label}, then in {_place(entry.path, home)} change "
        f"the entry {quoted(entry.name)} (keep its name) to start:",
        commands=lines, after=after)


def _new_spelling(old: str) -> Optional[str]:
    for new, earlier in names.SETTINGS.values():
        if earlier == old:
            return new
    return None


# ---------------------------------------------------------------------------
# The desktop extension, when it is older than the pointer
# ---------------------------------------------------------------------------

class OldExtension:
    """A desktop extension that would still start the old code: its
    manifest names qualcoder-mcp below 0.14.1, or it holds the old
    package's server and not Exegete's (the published 0.14.0 package
    lays out src/qualcoder_mcp/server.py; Exegete's has src/exegete)."""

    def __init__(self, folder: Path, version: str):
        self.folder, self.version = folder, version

    def label(self, home: Path) -> str:
        version = (f", qualcoder-mcp {_word(self.version)}," if self.version
                   else "")
        return f"the desktop extension{version} in {_place(self.folder, home)}"


def _exists(path: Path) -> bool:
    try:
        return os.path.lexists(path)
    except (OSError, ValueError):
        return False


def old_extensions(home: Path) -> List[OldExtension]:
    found = []
    for parent in extension_folders(home):
        try:
            folders = sorted(parent.iterdir())
        except OSError:
            continue
        for folder in folders:
            try:
                if not folder.is_dir():
                    continue
            except OSError:
                continue
            manifest = _read_json(folder / "manifest.json") or {}
            version = manifest.get("version")
            version = version if isinstance(version, str) else ""
            named = manifest.get("name") == names.OLD_DISTRIBUTION
            old_code = (_is_file(folder / "src" / names.OLD_PACKAGE /
                                 "server.py") and
                        not _exists(folder / "src" / names.PACKAGE))
            if (named and not is_pointer(version)) or old_code:
                found.append(OldExtension(folder, version if named else ""))
    return found


def _extension_finding(extension: OldExtension, home: Path) -> Finding:
    label = extension.label(home)
    return Finding(
        f"{label[0].upper()}{label[1:]} is older than Exegete: it still "
        f"starts the earlier code, which uses "
        f"{_place(state_folder.old_path(home), home)}.",
        "Update it: open the Exegete extension's file "
        "(exegete-<version>.mcpb) with Claude Desktop, which replaces this "
        "one and keeps its settings (INSTALL.md, \"Coming from "
        "qualcoder-mcp\"). If you no longer use it, remove it in Claude "
        "Desktop's settings instead.")


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


# ps by its full path, never a name looked up on the PATH (which could
# lead to another program that says nothing runs).
POSIX_PS = ("/bin/ps", "/usr/bin/ps")


def posix_ps() -> Optional[str]:
    for path in POSIX_PS:
        if os.path.isfile(path):
            return path
    return None


Row = Tuple[int, int, Optional[int], str]


def _process_table() -> Optional[List[Row]]:
    """(process id, parent's id, when it started, command line) for every
    process, or None when it cannot be read (then nothing is removed).
    When it started is read on Windows alone (None elsewhere), where a
    dead parent's number stays on its child and can be taken by a later
    program; on macOS and Linux an orphan is given a new parent."""
    windows = os.name == "nt"
    if windows:
        powershell = windows_powershell()
        if powershell is None:
            return None
        cmd = [powershell, "-NoProfile", "-Command",
               "Get-CimInstance Win32_Process | ForEach-Object "
               "{ \"$($_.ProcessId) $($_.ParentProcessId) "
               "$(if ($_.CreationDate) "
               "{ $_.CreationDate.ToFileTimeUtc() } else { 0 }) "
               "$($_.CommandLine)\" }"]
    else:
        ps = posix_ps()
        if ps is None:
            return None
        cmd = [ps, "-axo", "pid=,ppid=,args="]
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=20,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    rows: List[Row] = []
    numbers = 3 if windows else 2
    for row in done.stdout.decode("utf-8", errors="replace").splitlines():
        parts = row.strip().split(None, numbers)
        if len(parts) >= numbers and all(p.isdigit()
                                         for p in parts[:numbers]):
            rows.append((int(parts[0]), int(parts[1]),
                         (int(parts[2]) or None) if windows else None,
                         parts[numbers] if len(parts) > numbers else ""))
    return rows


def _own_ids() -> Tuple[int, int]:
    """This process's id and its parent's."""
    return os.getpid(), os.getppid()


def _listing() -> Optional[List[str]]:
    """Every other process's command line, or None when it cannot be
    read. The check itself and the programs that started it (uvx, pip's
    launcher on Windows, the shell) are left out: they are not an older
    copy of the server, whatever their command line says. Nothing else
    is: a program naming --check-transition may be an older copy that
    ignores its arguments (0.10 and 0.11 do)."""
    rows = _process_table()
    if rows is None:
        return None
    parent = {pid: ppid for pid, ppid, _, _ in rows}
    started = {pid: when for pid, _, when, _ in rows}
    child, current = _own_ids()
    mine = {child}
    for _ in range(256):                         # a loop in the table ends
        if not current or current in mine:
            break
        born, child_born = started.get(current), started.get(child)
        if born and child_born and born > child_born:
            break                        # the number is a later program's
        mine.add(current)
        child, current = current, parent.get(current)
    return [args for pid, _, _, args in rows if pid not in mine]


def started_as_old(lines: Iterable[str]) -> List[str]:
    """The command lines that run the old command or module."""
    hits = []
    for line in lines:
        words = [w.strip("\"'") for w in line.split()]
        if any(_OLD_ARG.search(w) for w in words) or _OLD_MODULE in words:
            hits.append(line[:200])
    return hits


# ---------------------------------------------------------------------------
# The state folder's link, the old logs and the old projects folder
# ---------------------------------------------------------------------------

def _remove_link(link: Path, home: Path) -> Tuple[bool, str]:
    """Remove the link (a junction on Windows) and never what it leads to;
    refuse anything that is not a link to ~/.exegete by then."""
    new = link.with_name(names.STATE_FOLDER)
    shown, shown_new = _place(link, home), _place(new, home)
    if not state_folder.is_link(link) or \
            not state_folder.same_folder(link, new):
        return False, f"Left {shown}: it is no longer a link to {shown_new}."
    try:
        if os.name == "nt" and not os.path.islink(link):
            os.rmdir(link)                    # a junction: the link alone
        else:
            os.unlink(link)
    except OSError as error:
        return False, f"Could not remove {shown} ({type(error).__name__})."
    return True, f"Removed the link {shown}; {shown_new} is untouched."


def state_link(home: Path, busy: Optional[List[str]],
               holders: Iterable[str] = ()) -> List[Finding]:
    """`holders`: what could still start an older copy that uses the link
    (an old package below 0.14.1, a host's entry for the old command)."""
    old = state_folder.old_path(home)
    new = state_folder.new_path(home)
    shown, shown_new = _place(old, home), _place(new, home)
    holders = list(holders)
    if not os.path.lexists(old):
        return []
    if not state_folder.is_link(old) and not os.path.lexists(new):
        return [Finding(
            f"{shown} has not been moved to {shown_new} yet.",
            "Start Exegete once through your AI host: its first start moves "
            "the folder whole and leaves a link under the old name. Then "
            "run the check again.")]
    if not state_folder.is_link(old):
        return [Finding(
            f"{shown} is a folder of its own, beside {shown_new}: an older "
            f"copy of the server (0.14 or earlier) made it, with a secret "
            f"key of its own, which Exegete does not use.",
            "Quit or update that older copy first. Keeping the folder changes "
            "nothing for Exegete; removing it removes that copy's secret, "
            "sessions and privacy run records, so it is yours to decide. "
            "This check never removes a folder.")]
    if not state_folder.same_folder(old, new) or not new.is_dir():
        return [Finding(
            f"{shown} is a link that does not lead to {shown_new}.",
            "See where it leads before removing it yourself; this check "
            "removes only a link to Exegete's own folder.")]
    if busy is None:
        return [Finding(
            f"{shown} is the link the move left, leading to {shown_new}.",
            "Whether a program started as qualcoder-mcp is still running "
            "could not be read, so the link stays; quit every AI host, "
            "then run the check again.")]
    if busy:
        return [Finding(
            f"{shown} is the link the move left, leading to {shown_new}; a "
            f"program started as qualcoder-mcp is running and may still "
            f"use it.",
            "Quit it (and change its entry, above) first, then run "
            "`exegete --check-transition --tidy`.")]
    if holders:
        return [Finding(
            f"{shown} is the link the move left, leading to {shown_new}. "
            f"Nothing started as qualcoder-mcp is running, but an older "
            f"copy could still be started: " + "; ".join(holders) + ".",
            "The link stays until the steps above are done: an older copy "
            "started without it would make a folder of its own, with a "
            "second secret key. Then run `exegete --check-transition "
            "--tidy`.")]
    return [Finding(
        f"{shown} is the link the move left, leading to {shown_new}, and "
        f"nothing started as qualcoder-mcp is running or left to start.",
        "`exegete --check-transition --tidy` removes the link (only the "
        "link: the folder it leads to is untouched). This check cannot see "
        "an older copy started from a project's own .mcp.json file: keep "
        "the link while one could still start.",
        tidy=lambda: _remove_link(old, home))]


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
            f"{_place(folder, home)}: {', '.join(p.name for p in logs)}.",
            step, tidy=tidy, is_log=True))
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


def _projects_in(folder: Path) -> Tuple[List[str], List[str]]:
    """(projects, backups) in `folder`, as paths relative to it: every
    `*.qda` up to three levels down, as list_available_projects counts
    depth; a project folder is not searched inside."""
    projects: List[str] = []
    backups: List[str] = []
    for root, folders, files in os.walk(folder):
        relative = Path(root).relative_to(folder)
        for name in sorted(folders + files):
            if name.lower().endswith(".qda"):
                stem = name[:-4]
                (backups if "_backup_" in stem or "_BKUP_" in stem
                 else projects).append(str(relative / name))
        folders[:] = sorted(
            f for f in folders if not f.lower().endswith(".qda")
            and len(relative.parts) + 1 < PROJECT_DEPTH)
    return projects, backups


def old_projects_folder(home: Path) -> List[Finding]:
    folder = home / "Documents" / names.OLD_WORKSPACE_FOLDER
    try:
        with os.scandir(folder) as entries:
            top = sorted(e.name for e in entries)
    except OSError:
        return []
    shown = _place(folder, home)
    if not top:
        return [Finding(
            f"{shown}, the earlier projects folder, is empty.",
            "You may remove it yourself if you no longer want it; this check "
            "never removes a folder.")]
    projects, backups = _projects_in(folder)
    others = [name for name in top if not name.lower().endswith(".qda")]
    held = []
    if projects:
        held.append(f"{_count(len(projects), 'project')}, up to three "
                    f"folders down: {_listed(projects)}")
    if backups:
        held.append(f"{_count(len(backups), 'backup')}: {_listed(backups)}")
    if others:
        held.append(("and at its top level " if held else "") +
                    f"{_listed(others)}")
    if projects or backups:
        what = (f"{shown}, the earlier projects folder, holds " +
                "; ".join(held) + ".")
        step = ("Nothing to do: Exegete never moves or empties it, and "
                "list_available_projects still searches it, as part of "
                "Documents. To keep working there, set EXEGETE_WORKSPACE "
                "to it.")
    else:
        what = (f"{shown}, the earlier projects folder, holds no project "
                f"within three folders of it, but it is not empty: "
                f"{_listed(others)}.")
        step = ("Nothing to do: look through what is there before you "
                "decide whether to keep it.")
    return [Finding(what, step + " This check never removes a folder.",
                    left=False)]


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
    """Everything, read-only, in the order to take the steps: Exegete
    where it is missing, then the hosts' entries, then the old package,
    then the link, the logs and the projects folder."""
    home = Path.home() if home is None else Path(home)
    lines = listing()
    busy = None if lines is None else started_as_old(lines)
    entries = old_entries(home)
    installs = old_installs(home, prefix, which, entries)
    holders = [f"qualcoder-mcp {_word(i.version)} in {_place(i.root, home)}"
               for i in installs if not i.pointer]
    holders += [f"{e.label}'s entry {quoted(e.name)}" for e in entries]
    extensions = old_extensions(home)
    holders += [x.label(home) for x in extensions]
    return ([_install_finding(i, home) for i in installs
             if i.needs_exegete] +
            [_entry_finding(e, home, which, installs) for e in entries] +
            [_removal_finding(i, home) for i in installs] +
            [_extension_finding(x, home) for x in extensions] +
            state_link(home, busy, holders) + old_logs(home, busy) +
            old_projects_folder(home))


def run(tidy: bool = False, tidy_old_logs: bool = False,
        out=None, **where) -> int:
    """Print the check (and, with `tidy`, what it removed); the exit code
    is 0 when nothing is left behind, else 1."""
    out = sys.stdout if out is None else out
    findings = check(**where)
    print(HEADING, file=out)
    print("", file=out)
    if not any(f.left for f in findings):
        print(NOTHING_LEFT, file=out)
    left = 0
    for number, finding in enumerate(findings, 1):
        print(f"{number}. {finding.what}", file=out)
        print(f"   What to do: {finding.step}", file=out)
        for line in finding.commands:
            print(f"       {line}", file=out)
        if finding.after:
            print(f"   {finding.after}", file=out)
        if tidy and finding.tidy is not None and \
                (tidy_old_logs or not finding.is_log):
            done, text = finding.tidy()
            print(f"   {'Done' if done else 'Not done'}: {text}", file=out)
            if done:
                continue
        if finding.left:
            left += 1
    print("", file=out)
    print("Read-only unless --tidy was given; projects, backups and hosts' "
          "configuration files are never changed.", file=out)
    return 0 if left == 0 else 1
