# SPDX-License-Identifier: LGPL-3.0-or-later
"""The server's settings, read under both spellings (v0.14.1).

Every setting this server reads from its environment is read here and
nowhere else (tests/test_v0141_compat.py forbids any other environment
read in the package). Each has a new spelling, starting EXEGETE_, and
the earlier one, which is still read until v1.0 (names.SETTINGS); the
two settings of the check for new versions have the new spelling only
(names.NEW_ONLY_SETTINGS, read by update_check and installed_as). The
one other read here is not a setting: Windows' own folder, SystemRoot,
from which the transition check starts PowerShell by its full path.

The rule when both spellings are set:

- only the new one: used, silently;
- only the earlier one: used, and the server's start-up log says once
  which spelling to use instead, and until when the earlier one works;
- both, saying the same thing: used, silently;
- both, saying different things: the server does not start, and says
  which two spellings disagree (never their values);
- a workspace is required if either spelling of
  EXEGETE_WORKSPACE_REQUIRED says 1.

"The same thing" is judged after each value is tidied exactly as its
read tidies it (spaces stripped where the read strips them, the tool set
in lower case, a workspace path with `~` expanded, the two switches
compared as "is it 1", the AI coder name after validate_coder_name), and
a blank value counts as unset. The value then used is the raw text of
the spelling chosen, so it behaves exactly as it did before the rename.
"""

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional

from . import names


class Reading(NamedTuple):
    """One setting as read: the raw value (None when neither spelling is
    set), the spelling it came from (the new one when neither is set, so
    a message has a name to give), whether only the earlier spelling was
    set, and whether the two spellings disagree."""
    value: Optional[str]
    name: str
    old_only: bool
    conflict: bool


def _blank(value: Optional[str]) -> bool:
    return value is None or not value.strip()


def _toolset(value: str) -> Any:
    return value.strip().lower()


def _coder_name(value: str) -> Any:
    from .database import validate_coder_name     # no import cycle
    try:
        return validate_coder_name(value, "name")
    except ValueError:
        return ("not a valid coder name", value.strip())


def _path(value: str) -> Any:
    try:
        return str(Path(value).expanduser())
    except (RuntimeError, ValueError):
        return ("not a path", value)


def _required_switch(value: str) -> Any:
    return value.strip() == "1"


def _exact_switch(value: str) -> Any:
    return value == "1"


def _as_given(value: str) -> Any:
    return value


# How each read tidies its value today, which is how the two spellings
# are compared.
NORMALISE: Dict[str, Callable[[str], Any]] = {
    "toolset": _toolset,
    "ai_coder_name": _coder_name,
    "workspace": _path,
    "workspace_required": _required_switch,
    "allow_unknown_schema": _exact_switch,
    "project_path": _as_given,
}


def new_name(key: str) -> str:
    return names.SETTINGS[key][0]


def old_name(key: str) -> str:
    return names.SETTINGS[key][1]


def read(key: str, environ: Optional[Mapping[str, str]] = None) -> Reading:
    """Setting `key` (a key of names.SETTINGS) from `environ`, by default
    this process's environment."""
    env = os.environ if environ is None else environ
    new, old = names.SETTINGS[key]
    new_raw, old_raw = env.get(new), env.get(old)
    if not _blank(new_raw) and not _blank(old_raw):
        normalise = NORMALISE[key]
        new_value, old_value = normalise(new_raw), normalise(old_raw)
        if key == "workspace_required":
            # Required if either says so: the safer reading
            if not new_value and old_value:
                return Reading(old_raw, old, False, False)
            return Reading(new_raw, new, False, False)
        return Reading(new_raw, new, False, new_value != old_value)
    if not _blank(old_raw):
        return Reading(old_raw, old, True, False)
    if not _blank(new_raw):
        return Reading(new_raw, new, False, False)
    # Neither says anything: a blank one is still handed on as it is, so
    # a read that treats a blank value in its own way (a blank coder name
    # stops the server) goes on doing so.
    if new_raw is not None:
        return Reading(new_raw, new, False, False)
    if old_raw is not None:
        return Reading(old_raw, old, False, False)
    return Reading(None, new, False, False)


def value(key: str, environ: Optional[Mapping[str, str]] = None
          ) -> Optional[str]:
    """Only the value of `read(key)`."""
    return read(key, environ).value


def conflicts(environ: Optional[Mapping[str, str]] = None) -> List[str]:
    """The start-up refusal for every setting whose two spellings
    disagree, in words that name the spellings and never the values."""
    found = []
    for key in names.SETTINGS:
        if read(key, environ).conflict:
            new, old = names.SETTINGS[key]
            found.append(
                f"{new} and {old} are both set and say different things. "
                f"They are two spellings of one setting ({old} is the "
                f"earlier one, read until {names.OLD_SPELLINGS_UNTIL}): "
                f"remove one of them from the host's configuration, or "
                f"make them the same.")
    return found


def old_spellings_in_use(environ: Optional[Mapping[str, str]] = None
                         ) -> List[str]:
    """One log line for each setting given only under its earlier
    spelling."""
    lines = []
    for key in names.SETTINGS:
        if read(key, environ).old_only:
            new, old = names.SETTINGS[key]
            lines.append(
                f"{old} is the earlier spelling of {new}; it is read "
                f"until {names.OLD_SPELLINGS_UNTIL}. Use {new} in the "
                f"host's configuration instead.")
    return lines


def reader_process_environment() -> Dict[str, str]:
    """The few variables the document import's reading process is
    started with (0.14.3, provisional): the system path, the locale and,
    on Windows, the system root; never the host's other settings."""
    keep = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT", "SystemRoot")
    return {key: os.environ[key] for key in keep if key in os.environ}


def update_check(environ: Optional[Mapping[str, str]] = None
                 ) -> Optional[str]:
    """EXEGETE_UPDATE_CHECK, which has one spelling only (names.
    NEW_ONLY_SETTINGS): its raw value, or None when it is not set.
    updates.read_setting says what each value means."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["update_check"])


def installed_as(environ: Optional[Mapping[str, str]] = None
                 ) -> Optional[str]:
    """EXEGETE_INSTALLED_AS, the desktop extension's own mark: its raw
    value, or None when it is not set."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["installed_as"])


def windows_system_root() -> str:
    """Windows' own folder: SystemRoot, or C:\\Windows when it is unset
    or not a full path (a relative one would be looked up from the
    current folder)."""
    root = os.environ.get("SystemRoot", "")
    return root if os.path.isabs(root) else "C:\\Windows"


# The system's own values that reading a file on the computer needs
# (v0.14.3, provisional). Not settings: where this account's caches live,
# and whether there is a screen on which to open a window.

def windows_local_app_data() -> Optional[str]:
    """Windows' per-account folder for data that is neither roamed nor
    synced, LOCALAPPDATA, or None when it is unset or not a full path."""
    value = os.environ.get("LOCALAPPDATA", "")
    return value if os.path.isabs(value) else None


def xdg_cache_home() -> Optional[str]:
    """XDG_CACHE_HOME when it is a full path, else None (the XDG rules
    say a relative value is to be ignored)."""
    value = os.environ.get("XDG_CACHE_HOME", "")
    return value if os.path.isabs(value) else None


def remote_session() -> bool:
    """Whether this process runs in an SSH session, where a window would
    open on another computer's screen, or on none."""
    return any(os.environ.get(name)
               for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"))


def linux_display() -> bool:
    """Whether a Linux desktop session is reachable: DISPLAY (X11) or
    WAYLAND_DISPLAY is set."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
