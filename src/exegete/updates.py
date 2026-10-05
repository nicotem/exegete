# SPDX-License-Identifier: LGPL-3.0-or-later
"""Telling the researcher, once, that a newer version of Exegete exists.

The owner's ruling of 5 October 2026: Exegete may contact the network for
one purpose only, to learn whether a newer version exists. Everything
else here follows from the design reviewed before it was written:

- **One file, four values.** The only thing fetched is VERSION_FILE_URL,
  a small JSON file holding a format number, the newest version, its
  release date and whether it is important. Nothing else in it is read,
  and no text or link from the network ever reaches the conversation:
  every sentence and every link below is written here, and the only
  free text about a version is the installed version's own summary,
  built into the package (release.py).
- **The setting.** EXEGETE_UPDATE_CHECK (names.NEW_ONLY_SETTINGS). The
  desktop extension passes its box as "true" or "false" and checks by
  default; on the Terminal route the check is off unless switched on.
  An unrecognised value means off and is logged once; it never stops
  the server, since a server that does not start can never announce a
  fix. Switched off, Exegete makes no connection at all, including when
  asked whether it is up to date.
- **Told before anything connects.** The first answer after a start
  with the setting on carries a disclosure note for the assistant to
  pass on, and the first check waits at least FIRST_CHECK_WAIT after it.
- **At most once a week on its own, at most once a day when asked.**
  Counted from the last attempt, successful or not, so a network that
  blocks the check is not asked again at every start.
- **One notice per new version**, added once as a field of the next
  successful tool answer (`exegete_notice`), so that hosts which read
  only a tool's structured content (Codex) see it too.
- **A note after an update**, once, with the installed version's own
  summary.
- **Never a reason to fail.** Every network, file and parsing problem
  ends as "could not check" and one line in the log naming the kind of
  problem only.

The fetch uses the standard library only, verifies TLS with the
system's default context, follows no redirect, reads at most MAX_BYTES
and gives up after DEADLINE seconds in all (the socket's own timeout
covers one step at a time, so the whole fetch runs in a thread that is
abandoned at the deadline).
"""

import json
import logging
import os
import re
import socket
import ssl
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from . import env_settings, names, release
from .preview_tokens import ensure_state_dir, state_home

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Addresses. None is read from the network: each is fixed here, and the
# version-specific ones are built from a validated version number.
# ---------------------------------------------------------------------------

VERSION_FILE_URL = "https://nicotem.github.io/exegete/latest.json"
UPDATE_PAGE = "https://nicotem.github.io/exegete/update/"
_REPOSITORY = "https://github.com/nicotem/exegete"
INSTALL_UPDATING = (f"{_REPOSITORY}/blob/main/INSTALL.md"
                    f"#updating-the-mcp-server")
INSTALL_COMING_FROM = (f"{_REPOSITORY}/blob/main/INSTALL.md"
                       f"#coming-from-qualcoder-mcp")


def download_link(display: str) -> str:
    """The desktop extension's file for a release, by its display form."""
    return (f"{_REPOSITORY}/releases/download/v{display}/"
            f"exegete-{display}.mcpb")


def release_notes_link(display: str) -> str:
    return f"{_REPOSITORY}/releases/tag/v{display}"


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

STATE_FILENAME = "update_check.json"
STATE_MAX_BYTES = 16384
MAX_BYTES = 16384
DEADLINE = 8.0
DAY = 86400
CHECK_EVERY = 7 * DAY          # the check on its own
ASKED_REUSE = DAY              # the check when asked
FIRST_CHECK_WAIT = 7 * DAY     # after the disclosure note
ANNOUNCED_KEEP = 20
USER_AGENT = names.SERVER_NAME
TOOL_NAME = "check_for_updates"


# ---------------------------------------------------------------------------
# Versions: a strict subset of PEP 440, compared by hand (`packaging` is a
# development dependency only; tests/test_updates.py checks the order
# against it). The version also ends up in commands a researcher pastes
# into a terminal, so this pattern is the control on those commands.
# ---------------------------------------------------------------------------

_NUMBER = r"(0|[1-9][0-9]{0,3})"
_PUBLISHED = re.compile(
    rf"{_NUMBER}\.{_NUMBER}\.{_NUMBER}(?:(a|b|rc){_NUMBER})?", re.ASCII)
_INSTALLED = re.compile(
    rf"{_NUMBER}\.{_NUMBER}\.{_NUMBER}(?:(a|b|rc){_NUMBER})?"
    rf"(?:\.dev{_NUMBER})?", re.ASCII)
_DISPLAY_PRE = {"a": "alpha", "b": "beta", "rc": "rc"}
_PRE_RANK = {"a": 0, "b": 1, "rc": 2}


class Version(NamedTuple):
    major: int
    minor: int
    micro: int
    pre: Optional[str]
    pre_number: int
    dev: Optional[int]

    def key(self) -> Tuple:
        if self.pre is None:
            pre = (-1, 0) if self.dev is not None else (3, 0)
        else:
            pre = (_PRE_RANK[self.pre], self.pre_number)
        dev = (0, self.dev) if self.dev is not None else (1, 0)
        return (self.major, self.minor, self.micro) + pre + dev

    def pep440(self) -> str:
        text = f"{self.major}.{self.minor}.{self.micro}"
        if self.pre is not None:
            text += f"{self.pre}{self.pre_number}"
        if self.dev is not None:
            text += f".dev{self.dev}"
        return text

    def display(self) -> str:
        """The project's own spelling (pyproject.toml, the tags):
        0.15.0a0 is 0.15.0-alpha, 0.15.0b2 is 0.15.0-beta.2."""
        text = f"{self.major}.{self.minor}.{self.micro}"
        if self.pre is not None:
            text += f"-{_DISPLAY_PRE[self.pre]}"
            if self.pre_number:
                text += f".{self.pre_number}"
        if self.dev is not None:
            text += f".dev{self.dev}"
        return text


def _version(match: "re.Match[str]") -> Version:
    major, minor, micro, pre, pre_number = match.groups()[:5]
    dev = match.group(6) if match.re is _INSTALLED else None
    return Version(int(major), int(minor), int(micro), pre,
                   int(pre_number) if pre_number else 0,
                   int(dev) if dev is not None else None)


def parse_published(text: Any) -> Optional[Version]:
    """A version the version file may name: no early build, no local
    part, nothing around it."""
    if not isinstance(text, str):
        return None
    match = _PUBLISHED.fullmatch(text)
    return _version(match) if match else None


def parse_installed(text: Any) -> Optional[Version]:
    """The running version, or None when it cannot be told (a source
    tree without install reports 0.0.0+unknown, which is never "old")."""
    if not isinstance(text, str):
        return None
    match = _INSTALLED.fullmatch(text)
    return _version(match) if match else None


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def parse_date(text: Any, today: date) -> Optional[date]:
    """An ISO date, never more than two days ahead of today."""
    if not isinstance(text, str) or not _DATE.fullmatch(text):
        return None
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return None
    return None if day > today + timedelta(days=2) else day


def spoken_date(day: date) -> str:
    return f"{day.day} {_MONTHS[day.month - 1]} {day.year}"


def _today(now: float) -> date:
    return datetime.fromtimestamp(now, tz=timezone.utc).date()


# ---------------------------------------------------------------------------
# The version file
# ---------------------------------------------------------------------------

class Published(NamedTuple):
    version: Version
    released: date
    important: bool


class CheckFailed(Exception):
    """The check could not be made; `kind` is a short plain name for why,
    the only thing about it that is logged or shown."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


NO_CONNECTION = "no connection"
TIMED_OUT = "no answer in time"
UNTRUSTED = "certificate not trusted"
REFUSED = "the website refused"
REDIRECTED = "the website redirected"
NOT_EXPECTED = "not the expected file"
TOO_LARGE = "the answer was too large"
NOT_ALLOWED = "address not allowed"


def _refuse_constant(name: str) -> Any:
    raise ValueError(f"{name} is not allowed")


def _no_duplicates(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def parse_version_file(raw: bytes, today: date) -> Published:
    """The four values, or CheckFailed(NOT_EXPECTED). Any other key is
    ignored; any malformed value refuses the whole file."""
    try:
        data = json.loads(raw.decode("utf-8"),
                          parse_constant=_refuse_constant,
                          object_pairs_hook=_no_duplicates)
    except Exception:          # RecursionError included
        raise CheckFailed(NOT_EXPECTED) from None
    if not isinstance(data, dict):
        raise CheckFailed(NOT_EXPECTED)
    form = data.get("format")
    if type(form) is not int or form != 1:
        raise CheckFailed(NOT_EXPECTED)
    version = parse_published(data.get("version"))
    released = parse_date(data.get("released"), today)
    important = data.get("important")
    if version is None or released is None or type(important) is not bool:
        raise CheckFailed(NOT_EXPECTED)
    return Published(version, released, important)


# ---------------------------------------------------------------------------
# The fetch
# ---------------------------------------------------------------------------

_LOOPBACK = ("127.0.0.1", "::1", "localhost")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Every 3xx becomes an error: the file is fetched from one address
    and nowhere else."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener(url: str) -> urllib.request.OpenerDirector:
    parts = urllib.parse.urlsplit(url)
    loopback = parts.hostname in _LOOPBACK
    # https only; plain http only to this computer (the tests' server)
    if parts.scheme != "https" and not (parts.scheme == "http"
                                        and loopback):
        raise CheckFailed(NOT_ALLOWED)
    if parts.username or parts.password:
        raise CheckFailed(NOT_ALLOWED)
    proxies = (urllib.request.ProxyHandler({}) if loopback
               else urllib.request.ProxyHandler())
    return urllib.request.build_opener(
        proxies,
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirect())


def _fetch_once(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _opener(url).open(request, timeout=DEADLINE) as response:
            encoding = (response.headers.get("Content-Encoding") or
                        "identity").strip().lower()
            if encoding != "identity":
                raise CheckFailed(NOT_EXPECTED)
            raw = response.read(MAX_BYTES + 1)
    except CheckFailed:
        raise
    except urllib.error.HTTPError as error:
        raise CheckFailed(REDIRECTED if 300 <= error.code < 400
                          else REFUSED) from None
    except urllib.error.URLError as error:
        reason = error.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            raise CheckFailed(UNTRUSTED) from None
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise CheckFailed(TIMED_OUT) from None
        raise CheckFailed(NO_CONNECTION) from None
    except ssl.SSLCertVerificationError:
        raise CheckFailed(UNTRUSTED) from None
    except (socket.timeout, TimeoutError):
        raise CheckFailed(TIMED_OUT) from None
    except Exception:
        raise CheckFailed(NO_CONNECTION) from None
    if len(raw) > MAX_BYTES:
        raise CheckFailed(TOO_LARGE)
    return raw


def fetch(url: Optional[str] = None, deadline: Optional[float] = None
          ) -> bytes:
    """The version file's bytes, within one overall deadline. The work
    runs in a daemon thread, abandoned if it outlives the deadline (a
    name lookup has no timeout of its own, and a server sending a byte
    at a time would keep a read alive)."""
    target = VERSION_FILE_URL if url is None else url
    limit = DEADLINE if deadline is None else deadline
    outcome: Dict[str, Any] = {}

    def work():
        try:
            outcome["raw"] = _fetch_once(target)
        except CheckFailed as error:
            outcome["error"] = error
        except BaseException:           # never let a thread die loudly
            outcome["error"] = CheckFailed(NO_CONNECTION)

    worker = threading.Thread(target=work, name="exegete-update-check",
                              daemon=True)
    worker.start()
    worker.join(limit)
    if worker.is_alive() or not outcome:
        raise CheckFailed(TIMED_OUT)
    if "error" in outcome:
        raise outcome["error"]
    return outcome["raw"]


# ---------------------------------------------------------------------------
# The state file: what was checked, announced and run on this computer.
# Shared by every Exegete on the computer (the extension and a Terminal
# copy may both run), so each write re-reads the file under the lock and
# changes it only in ways that merge: maxima, unions, the earliest
# disclosure.
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _state_file(folder: Optional[Path] = None) -> Path:
    return (state_home() if folder is None else folder) / STATE_FILENAME


def _int_or_none(value: Any, now: float) -> Optional[int]:
    if type(value) is not int or value < 0 or value > now + DAY:
        return None
    return value


def read_state(now: Optional[float] = None,
               folder: Optional[Path] = None) -> Dict[str, Any]:
    """The state as stored, every value checked; anything malformed is
    treated as absent, and a missing or unreadable file as empty."""
    now = time.time() if now is None else now
    try:
        with open(_state_file(folder), "rb") as handle:
            raw = handle.read(STATE_MAX_BYTES + 1)
        if len(raw) > STATE_MAX_BYTES:
            return {}
        data = json.loads(raw.decode("utf-8"),
                          parse_constant=_refuse_constant)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    state: Dict[str, Any] = {}
    for key in ("last_attempt", "disclosed_at", "first_check_after"):
        value = _int_or_none(data.get(key), now if key != "first_check_after"
                             else now + FIRST_CHECK_WAIT + DAY)
        if value is not None:
            state[key] = value
    error = data.get("last_error")
    if error in (NO_CONNECTION, TIMED_OUT, UNTRUSTED, REFUSED, REDIRECTED,
                 NOT_EXPECTED, TOO_LARGE, NOT_ALLOWED):
        state["last_error"] = error
    newest = data.get("newest")
    if isinstance(newest, dict):
        try:
            published = parse_version_file(
                json.dumps({"format": 1, **{k: newest.get(k) for k in
                            ("version", "released", "important")}}
                           ).encode("utf-8"),
                _today(now))
            state["newest"] = published
        except CheckFailed:
            pass
    announced = data.get("announced")
    if isinstance(announced, list):
        state["announced"] = [v for v in announced[:ANNOUNCED_KEEP]
                              if parse_published(v) is not None]
    highest = parse_installed(data.get("highest_version_run"))
    if highest is not None:
        state["highest_version_run"] = highest
    return state


def _serialise(state: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"format": 1}
    for key in ("last_attempt", "last_error", "disclosed_at",
                "first_check_after"):
        if state.get(key) is not None:
            out[key] = state[key]
    newest = state.get("newest")
    if newest is not None:
        out["newest"] = {"version": newest.version.pep440(),
                         "released": newest.released.isoformat(),
                         "important": newest.important}
    if state.get("announced"):
        out["announced"] = list(state["announced"])
    if state.get("highest_version_run") is not None:
        out["highest_version_run"] = state["highest_version_run"].pep440()
    return out


def update_state(change: Callable[[Dict[str, Any]], None],
                 now: Optional[float] = None,
                 folder: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Re-read the state, apply `change` to it, and write it back in one
    atomic replace (a temp file made exclusively, owner-only, as the
    last-used project hint is). Returns the new state, or None when it
    could not be written; never raises. `folder` is the state folder
    as chosen by the caller: a check running in the background resolves
    it when it starts, not when it ends."""
    now = time.time() if now is None else now
    with _LOCK:
        tmp: Optional[Path] = None
        try:
            folder = state_home() if folder is None else folder
            ensure_state_dir(folder)
            state = read_state(now, folder)
            change(state)
            fd, name = tempfile.mkstemp(dir=folder,
                                        prefix=f"{STATE_FILENAME}.",
                                        suffix=".tmp")
            tmp = Path(name)
            try:
                handle = os.fdopen(fd, "w", encoding="utf-8")
            except BaseException:
                os.close(fd)
                raise
            with handle:
                json.dump(_serialise(state), handle)
            tmp.replace(_state_file(folder))
            return state
        except Exception as error:
            logger.debug("Could not record the check for new versions: %s",
                         type(error).__name__)
            if tmp is not None:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            return None


def _raise_highest(version: Version) -> Callable[[Dict[str, Any]], None]:
    def change(state):
        old = state.get("highest_version_run")
        if old is None or version.key() > old.key():
            state["highest_version_run"] = version
    return change


def _announce(version: Version) -> Callable[[Dict[str, Any]], None]:
    def change(state):
        listed = [v for v in state.get("announced", [])
                  if v != version.pep440()]
        state["announced"] = ([version.pep440()] + listed)[:ANNOUNCED_KEEP]
    return change


def _disclose(now: float) -> Callable[[Dict[str, Any]], None]:
    def change(state):
        # The earliest disclosure stands: another copy of Exegete on this
        # computer may have given it already
        if state.get("disclosed_at") is None:
            state["disclosed_at"] = int(now)
            state["first_check_after"] = int(now + FIRST_CHECK_WAIT)
    return change


def _attempted(now: float, published: Optional[Published],
               error: Optional[str]) -> Callable[[Dict[str, Any]], None]:
    def change(state):
        if state.get("last_attempt") is not None and \
                state["last_attempt"] > now:
            return          # another copy checked more recently
        state["last_attempt"] = int(now)
        if published is not None:
            state["newest"] = published
            state.pop("last_error", None)
        else:
            state["last_error"] = error
    return change


# ---------------------------------------------------------------------------
# The setting and the way Exegete was installed
# ---------------------------------------------------------------------------

_ON = ("on", "true", "1")
_OFF = ("off", "false", "0")

EXTENSION = "extension"
OLD_NAME = "old name"
PIPX = "pipx"
UV_TOOL = "uv tool"
SOURCE = "source"
UVX = "uvx"
PIP = "pip"
UNKNOWN = "unknown"

ROUTE_WORDS = {
    EXTENSION: "the Claude Desktop extension",
    OLD_NAME: "the earlier name, qualcoder-mcp",
    PIPX: "pipx",
    UV_TOOL: "uv tool",
    SOURCE: "a copy of the source",
    UVX: "uvx",
    PIP: "pip, in a virtual environment",
    UNKNOWN: "a way Exegete cannot tell",
}


def read_setting(route: str, environ=None) -> Tuple[bool, Optional[str]]:
    """(on, a warning to log or None). The extension checks by default;
    the Terminal route does not."""
    raw = env_settings.update_check(environ)
    default = route == EXTENSION
    if raw is None or not raw.strip() or raw.strip().startswith("${"):
        return default, None
    word = raw.strip().lower()
    if word in _ON:
        return True, None
    if word in _OFF:
        return False, None
    name = names.NEW_ONLY_SETTINGS["update_check"]
    return False, (f"{name} is not one of on, off, true, false, 1 or 0, so "
                   f"the check for new versions is off.")


def _direct_url() -> Optional[Dict[str, Any]]:
    try:
        from importlib.metadata import distribution
        text = distribution(names.DISTRIBUTION).read_text("direct_url.json")
        data = json.loads(text) if text else None
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _source_folder() -> Optional[Path]:
    """The folder of an editable install made from a git copy."""
    data = _direct_url()
    if not data or not (data.get("dir_info") or {}).get("editable"):
        return None
    url = data.get("url")
    if not isinstance(url, str) or not url.startswith("file://"):
        return None
    try:
        from urllib.request import url2pathname
        folder = Path(url2pathname(urllib.parse.urlsplit(url).path))
        return folder if (folder / ".git").exists() else None
    except Exception:
        return None


def detect_route(started_as: Optional[str] = None, environ=None,
                 prefix: Optional[str] = None) -> str:
    """How this copy was installed, in the order the design gives: the
    extension's own mark, the old name, uv tool or pipx, a git copy,
    uvx, a virtual environment; otherwise unknown."""
    if (env_settings.installed_as(environ) or "").strip().lower() == \
            EXTENSION:
        return EXTENSION
    if started_as:
        return OLD_NAME
    root = Path(sys.prefix if prefix is None else prefix)
    from .transition import _tool_kind     # no import cycle at load
    kind = _tool_kind(root)
    if kind == "uv tool":
        return UV_TOOL
    if kind == "pipx":
        return PIPX
    if prefix is None and _source_folder() is not None:
        return SOURCE
    parts = [part.lower() for part in root.parts]
    if "archive-v0" in parts and "uv" in " ".join(parts):
        return UVX
    if prefix is None and sys.prefix != sys.base_prefix:
        return PIP
    return UNKNOWN


# ---------------------------------------------------------------------------
# Commands, written for the shell of this computer. Paths are written from
# the home folder ($HOME expands inside double quotes in both shells; `~`
# does not), so the account name stays out of the conversation.
# ---------------------------------------------------------------------------

_POSIX_REFUSED = set("'\"`$!\\")
_WINDOWS_REFUSED = set("'\"`$")


def shell_path(path: Path, windows: bool) -> Optional[str]:
    """`path` as a command may quote it, or None when it holds a
    character no quoting here can carry safely."""
    from .database import forbidden_display_char   # no import cycle
    try:
        home = Path.home()
        relative = path.relative_to(home)
        prefix = "$HOME"
    except ValueError:
        relative, prefix = path, ""
    text = (str(relative).replace("/", "\\") if windows
            else relative.as_posix())
    refused = _WINDOWS_REFUSED if windows else _POSIX_REFUSED
    if any(ch in refused for ch in text) or not text.isprintable() or \
            forbidden_display_char(text) is not None:
        return None
    if not prefix:
        return text
    if text in ("", "."):
        return prefix
    return prefix + ("\\" if windows else "/") + text


def _command(windows: bool, executable: str, rest: str) -> str:
    return (f'& "{executable}" {rest}' if windows
            else f'"{executable}" {rest}')


def _shell_name(windows: bool) -> str:
    return "PowerShell" if windows else "Terminal"


_QUIT_HOST = ("Quit the app that started Exegete (for example Claude "
              "Desktop, Claude Code or LM Studio), so that nothing is "
              "using it while it changes.")
_REOPEN_HOST = "Open the app again."


def _extension_steps(new: Version, windows: bool) -> List[str]:
    display = new.display()
    quit_step = (
        "Quit Claude Desktop completely, then open it again, so that it "
        "starts the new version. Closing its window is not enough. ")
    quit_step += (
        "On Windows: at the bottom right of the screen, near the clock, "
        "find the Claude Desktop icon (you may need to click the small "
        "upward arrow first), right-click it and choose Quit (or Exit). "
        if windows else
        "On a Mac: with Claude Desktop in front, press Cmd and Q together, "
        "or choose Quit from the app's menu at the top of the screen. ")
    quit_step += ("Wait until the Claude Desktop icon has gone, then open "
                  "the app again. If you are not sure it has quit, "
                  "restarting the computer always works.")
    return [
        f"Click this link to download the new version: "
        f"{download_link(display)}. When it has finished, your browser "
        f"shows the file in its list of downloads. Its name starts with "
        f"exegete-{display}.",
        "Click the file there, or double-click it in your Downloads "
        "folder. Claude Desktop opens and shows Exegete, with the same "
        "reminder as the first time to install only extensions you trust. "
        "Click Install. If Claude Desktop says it needs to fetch a few "
        "things, click Install again: it takes a minute and needs the "
        "internet. If nothing happens, or another program opens the file, "
        "open Claude Desktop's Settings, then Extensions, then Advanced "
        "settings, click Install Extension..., and choose the file.",
        quit_step,
    ]


def _python_path(windows: bool) -> Optional[str]:
    return shell_path(Path(sys.executable), windows)


def _terminal_steps(route: str, new: Version, windows: bool
                    ) -> Optional[List[str]]:
    """The steps for a Terminal route, or None when no safe command can
    be given (the update page and INSTALL.md are given instead)."""
    pin = new.pep440()
    shell = _shell_name(windows)
    if route == PIP:
        python = _python_path(windows)
        if python is None:
            return None
        command = _command(windows, python, f'-m pip install "exegete=={pin}"')
    elif route == OLD_NAME:
        # Only a plain virtual environment: in a uv tool or pipx one the
        # old name needs two names pinned in a form not yet tried, so the
        # update page and INSTALL.md are given instead
        from .transition import _tool_kind
        if new.major >= 1 or sys.prefix == sys.base_prefix or \
                _tool_kind(Path(sys.prefix)) is not None:
            return None
        python = _python_path(windows)
        if python is None:
            return None
        command = _command(windows, python,
                       f'-m pip install "qualcoder-mcp=={pin}" '
                       f'"exegete=={pin}"')
    elif route == PIPX:
        command = f'pipx install --force "exegete=={pin}"'
    elif route == UV_TOOL:
        command = f'uv tool install --force "exegete=={pin}"'
    elif route == SOURCE:
        folder = _source_folder()
        python = _python_path(windows)
        place = shell_path(folder, windows) if folder is not None else None
        if python is None or place is None:
            return None
        return [
            _QUIT_HOST,
            f'In {shell}, go to the copy\'s folder (cd "{place}"), then '
            f"run git fetch --tags, then git checkout v{new.display()}, "
            f"then {_command(windows, python, '-m pip install -e .')}",
            _REOPEN_HOST,
        ]
    else:
        return None
    return [_QUIT_HOST, f"In {shell}, run: {command}", _REOPEN_HOST]


# ---------------------------------------------------------------------------
# What this run knows, and the notes it gives once
# ---------------------------------------------------------------------------

class Note(NamedTuple):
    key: str            # "disclosure", "new version:<pep440>", "after update"
    text: str


class _Run:
    def __init__(self):
        self.started = False
        self.installed: Optional[Version] = None
        self.route = UNKNOWN
        self.on = False
        self.after_update = False
        self.recorded = False
        self.given: set = set()
        self.thread: Optional[threading.Thread] = None
        self.windows = os.name == "nt"


_run = _Run()


def reset_for_tests() -> None:
    """Forget what this run knows (tests start each case afresh)."""
    global _run
    _run = _Run()


def start(installed_version: str, started_as: Optional[str] = None,
          now: Optional[float] = None, environ=None) -> None:
    """Called once by main(), after the state folder is settled and
    before the server serves: log whether checking is on, decide which
    notes are due, record the version that runs here, and start the
    weekly check if it is due."""
    now = time.time() if now is None else now
    with _LOCK:
        _run.started = True
        _run.installed = parse_installed(installed_version)
        _run.route = detect_route(started_as, environ)
        _run.on, warning = read_setting(_run.route, environ)
    if warning:
        logger.warning(warning)
    logger.info("Checking for new versions: %s", "on" if _run.on else "off")
    if _run.installed is None:
        return
    existed = state_home().exists()
    state = read_state(now) if existed else {}
    highest = state.get("highest_version_run")
    if highest is not None:
        _run.after_update = _run.installed.key() > highest.key()
        _run.recorded = not _run.after_update
    else:
        # Exegete ran here before (its folder exists) but recorded no
        # version: an update from 0.14.1 or earlier. With checking on,
        # the disclosure says what is new that matters most.
        _run.after_update = existed and not _run.on
    if existed and not _run.recorded:
        _record_version(now)
    _maybe_check_in_background(now)


def _record_version(now: float) -> None:
    if _run.installed is not None and \
            update_state(_raise_highest(_run.installed), now) is not None:
        _run.recorded = True


def _check_due(state: Dict[str, Any], now: float) -> bool:
    if not _run.on or state.get("disclosed_at") is None:
        return False
    first = state.get("first_check_after")
    if first is None or now < first:
        return False
    last = state.get("last_attempt")
    return last is None or now - last >= CHECK_EVERY


def check_now(now: Optional[float] = None,
              folder: Optional[Path] = None) -> Dict[str, Any]:
    """Fetch and record the version file now; returns the new state.
    Never raises."""
    now = time.time() if now is None else now
    folder = state_home() if folder is None else folder
    try:
        published = parse_version_file(fetch(), _today(now))
        error = None
    except CheckFailed as failure:
        published, error = None, failure.kind
        logger.info("The check for new versions could not be made: %s",
                    error)
    return (update_state(_attempted(now, published, error), now, folder)
            or read_state(now, folder))


def _maybe_check_in_background(now: float) -> None:
    with _LOCK:
        if _run.thread is not None and _run.thread.is_alive():
            return
        folder = state_home()
        if not _check_due(read_state(now, folder), now):
            return
        _run.thread = threading.Thread(target=check_now,
                                       args=(now, folder),
                                       name="exegete-weekly-check",
                                       daemon=True)
        _run.thread.start()


def _notice_text(published: Published, tool_available: bool) -> str:
    new = published.version.display()
    when = spoken_date(published.released)
    installed = _run.installed.display() if _run.installed else ""
    ask = ('To update, they can ask: "How do I update Exegete?"'
           if tool_available else f"To update, see {UPDATE_PAGE}")
    lead = "Note for the user, who sees it only if you pass it on. "
    if published.important:
        return (lead + "Pass it on calmly, once, after answering their "
                "request, and before making any further change to a "
                f"project. An important update to Exegete is available: "
                f"{new} ({when}). It fixes a problem that could affect "
                f"projects. They have {installed}. {UPDATE_PAGE} says what "
                f"the problem is and what to do until they update. {ask}")
    return (lead + "Pass it on once, in one or two sentences, after "
            "answering their request. Do not check for updates or start "
            "updating unless they ask. A newer version of Exegete is "
            f"available: {new} ({when}). They have {installed}, which "
            f"keeps working, so there is no hurry. What's new: "
            f"{UPDATE_PAGE}. {ask}")


def _disclosure_text(now: float, tool_available: bool) -> str:
    first = spoken_date(_today(now + FIRST_CHECK_WAIT))
    when_asked = ", and when they ask," if tool_available else ""
    switch = _switch_off_words(_run.route).replace(
        "To switch it off", "To switch it off before then or at any time")
    return ("Note for the user, who sees it only if you pass it on. Pass "
            "it on once, briefly, after answering their request. This "
            "version of Exegete can tell them when a new version is out. "
            f"Once a week at most{when_asked} it fetches a small file "
            "from its website, which GitHub hosts. Nothing from their "
            "projects is sent; GitHub records their computer's internet "
            "address and the time. It is switched on, and its first check "
            f"will be on or after {first}. {switch} PRIVACY.md, \"Checking "
            "for new versions\", says exactly what is sent.")


def _switch_off_words(route: str) -> str:
    if route == EXTENSION:
        return ("To switch it off: Claude Desktop's Settings, then "
                "Extensions, then Exegete, \"Tell me when a new version is "
                "out\".")
    return (f"To switch it off, set {names.NEW_ONLY_SETTINGS['update_check']}"
            f" to off in the settings of the app that starts Exegete.")


def _after_update_text() -> str:
    installed = _run.installed.display() if _run.installed else ""
    text = ("Note for the user, who sees it only if you pass it on. Pass "
            "it on once, briefly, after answering their request: Exegete "
            f"has been updated to {installed} on this computer, so the "
            "update worked.")
    if installed == release.VERSION:
        text += f" What's new: {release.SUMMARY}"
    return text + f" The full notes: {release_notes_link(installed)}."


def due_note(tool_available: bool, now: Optional[float] = None
             ) -> Optional[Note]:
    """The note the next successful tool answer should carry, or None.
    Cheap when nothing is due; also starts the weekly check when a
    server has run for a week, and records the version here once the
    state folder exists."""
    if not _run.started or _run.installed is None:
        return None
    now = time.time() if now is None else now
    if not _run.recorded and state_home().exists():
        _record_version(now)
    state = read_state(now) if (_run.on or _run.after_update) else {}
    if _run.on and state.get("disclosed_at") is None and \
            "disclosure" not in _run.given:
        return Note("disclosure", _disclosure_text(now, tool_available))
    if _run.after_update and "after update" not in _run.given:
        return Note("after update", _after_update_text())
    if _run.on:
        _maybe_check_in_background(now)
        newest = state.get("newest")
        if newest is not None and \
                newest.version.key() > _run.installed.key():
            key = f"new version:{newest.version.pep440()}"
            if key not in _run.given and \
                    newest.version.pep440() not in state.get("announced",
                                                             []):
                return Note(key, _notice_text(newest, tool_available))
    return None


def mark_given(note: Note, now: Optional[float] = None) -> None:
    now = time.time() if now is None else now
    with _LOCK:
        _run.given.add(note.key)
    if note.key == "disclosure":
        update_state(_disclose(now), now)
        if not _run.recorded:
            _record_version(now)
    elif note.key.startswith("new version:"):
        version = parse_published(note.key.split(":", 1)[1])
        if version is not None:
            update_state(_announce(version), now)


def attach(answer: Any, note: Note) -> Optional[str]:
    """`answer` with the note as its last field, `exegete_notice`, when
    it is a successful JSON object; else None (the note waits for the
    next answer). The tool's own text is kept as it was, byte for byte,
    up to the closing brace."""
    if not isinstance(answer, str):
        return None
    try:
        data = json.loads(answer)
    except ValueError:
        return None
    if not isinstance(data, dict) or "error" in data or \
            "exegete_notice" in data:
        return None
    body = answer.rstrip()
    if not body.endswith("}"):
        return None
    body = body[:-1].rstrip()
    field = '"exegete_notice": ' + json.dumps(note.text)
    joined = (body + "\n  " + field + "\n}" if body.endswith("{")
              else body + ",\n  " + field + "\n}")
    try:
        if json.loads(joined) != {**data, "exegete_notice": note.text}:
            return None
    except ValueError:
        return None
    return joined


# ---------------------------------------------------------------------------
# The tool's answer
# ---------------------------------------------------------------------------

def _installed_words() -> Tuple[str, Optional[str]]:
    installed = _run.installed.display() if _run.installed else "unknown"
    released = None
    if _run.installed is not None and installed == release.VERSION:
        try:
            released = spoken_date(date.fromisoformat(release.RELEASED))
        except ValueError:
            released = None
    return installed, released


def _you_have(installed: str, released: Optional[str]) -> str:
    return (f"You have {installed} ({released})." if released
            else f"You have {installed}.")


def tool_answer(now: Optional[float] = None,
                tool_available: bool = True) -> str:
    """check_for_updates' answer, as JSON. Makes at most one fetch, and
    none when checking is off, before the first-check date, or when an
    attempt was made in the last day."""
    now = time.time() if now is None else now
    if not _run.started:
        # A test, or an import without main(): read what main() would
        from . import __version__
        start(__version__, now=now)
    installed, released = _installed_words()
    answer: Dict[str, Any] = {
        "message": "",
        "steps": [],
        "installed_version": installed,
        "installed_released": released,
        "installed_as": ROUTE_WORDS[_run.route],
        "checking": "on" if _run.on else "off",
        "newest_version": None,
        "newest_released": None,
        "important": False,
        "up_to_date": None,
        "download_link": None,
        "release_notes": None,
        "instructions_page": UPDATE_PAGE,
    }
    have = _you_have(installed, released)

    def done(message: str) -> str:
        answer["message"] = message
        return json.dumps(answer, indent=2)

    if not _run.on:
        if _run.route == EXTENSION:
            how = ("To let Exegete check, open Claude Desktop's Settings, then "
                   "Extensions, then Exegete, and switch on \"Tell me when "
                   "a new version is out\".")
        else:
            how = (f"To let Exegete check, set "
                   f"{names.NEW_ONLY_SETTINGS['update_check']} to on in "
                   f"the settings of the app that starts it (INSTALL.md, "
                   f"\"Environment variables the server reads\").")
        return done("Checking for new versions is switched off, so Exegete "
                    f"made no connection. {have} You can look yourself at "
                    f"{UPDATE_PAGE}. {how}")
    if _run.installed is None:
        return done("Exegete cannot tell which version this is (it is "
                    "running from a copy that was not installed), so it "
                    f"cannot compare it with the newest. See {UPDATE_PAGE}.")
    state = read_state(now)
    prefix = ""
    if state.get("disclosed_at") is None:
        # The disclosure, said to the researcher in the answer itself
        mark_given(Note("disclosure", _disclosure_text(now, tool_available)),
                   now)
        prefix = ("This version of Exegete can tell you when a new version "
                  "is out. Once a week at most, and when you ask, it fetches "
                  "a small file from its website, which GitHub hosts. "
                  "Nothing from your projects is sent; GitHub records your "
                  "computer's internet address and the time. "
                  + _switch_off_words(_run.route) + " ")
        state = read_state(now)
    first = state.get("first_check_after")
    if first is None or now < first:
        day = spoken_date(_today(first if first is not None
                                 else now + FIRST_CHECK_WAIT))
        return done(prefix + f"Exegete's first check for new versions will "
                    f"be on {day}, as it says when this version is first "
                    f"used; until then it makes no connection. {have} You "
                    f"can look yourself at {UPDATE_PAGE}.")
    last = state.get("last_attempt")
    if last is None or now - last >= ASKED_REUSE:
        state = check_now(now)
    if state.get("last_error") is not None:
        return done(f"Exegete could not reach its website to check for a "
                    f"newer version ({state['last_error']}). The computer "
                    f"may be offline, or the network may block it. This "
                    f"does not affect anything else Exegete does. {have} "
                    f"You can look yourself at {UPDATE_PAGE}.")
    newest = state.get("newest")
    if newest is None:
        return done(f"Exegete has no answer from its website yet. {have} "
                    f"You can look yourself at {UPDATE_PAGE}.")
    new = newest.version.display()
    answer["newest_version"] = new
    answer["newest_released"] = spoken_date(newest.released)
    answer["important"] = newest.important
    order = (newest.version.key() > _run.installed.key()) - \
        (newest.version.key() < _run.installed.key())
    if order == 0:
        answer["up_to_date"] = True
        return done(f"You have the newest version of Exegete, {installed}"
                    f"{f' ({released})' if released else ''}. Exegete "
                    f"will tell you here when a newer one comes out.")
    if order < 0:
        answer["up_to_date"] = True
        return done(f"You have {installed}, which is newer than the newest "
                    f"published version, {new}. There is nothing to "
                    f"update.")
    answer["up_to_date"] = False
    answer["release_notes"] = release_notes_link(new)
    # The researcher has now been told: the notice is not repeated
    with _LOCK:
        _run.given.add(f"new version:{newest.version.pep440()}")
    update_state(_announce(newest.version), now)
    when = spoken_date(newest.released)
    second = ("It fixes a problem that could affect your projects: the page "
              "below says what it is, and what to do until you update."
              if newest.important else
              f"You have {installed}, which keeps working, so there is no "
              f"hurry.")
    if _run.route == EXTENSION:
        answer["download_link"] = download_link(new)
        answer["steps"] = _extension_steps(newest.version, _run.windows)
        return done(f"A newer version of Exegete is available: {new} "
                    f"({when}). {second} What's new, and pictures of each "
                    f"step: {UPDATE_PAGE}. Your projects stay as they are, "
                    f"and so do your conversations. After Claude Desktop "
                    f"reopens, the assistant may need to open your project "
                    f"again.")
    steps = _terminal_steps(_run.route, newest.version, _run.windows)
    if steps is None and _run.route == OLD_NAME:
        return done(f"A newer version of Exegete is available: {new} "
                    f"({when}). {second} This copy was started under "
                    f"Exegete's earlier name, qualcoder-mcp. INSTALL.md, "
                    f"\"Coming from qualcoder-mcp\", shows how to move to "
                    f"the new name and update: {INSTALL_COMING_FROM}.")
    if steps is None:
        return done(f"A newer version of Exegete is available: {new} "
                    f"({when}). {second} How to update depends on how "
                    f"Exegete was installed: {UPDATE_PAGE} shows the way "
                    f"for Claude Desktop, and INSTALL.md, \"Updating the MCP "
                    f"Server\", the Terminal route: {INSTALL_UPDATING}.")
    answer["steps"] = steps
    message = (f"A newer version of Exegete is available: {new} ({when}). "
               f"{second} What's new: {UPDATE_PAGE}.")
    if _run.route == OLD_NAME and newest.version.major < 1:
        message += (" qualcoder-mcp is Exegete's earlier name. Its last "
                    "release comes with Exegete 1.0, and its earlier setting "
                    "names are read only until then, so move to the new name "
                    "before 1.0: INSTALL.md, \"Coming from qualcoder-mcp\", "
                    f"has the steps: {INSTALL_COMING_FROM}.")
    return done(message)
