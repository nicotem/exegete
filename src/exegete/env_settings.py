# SPDX-License-Identifier: LGPL-3.0-or-later
"""The server's settings, read under both spellings (v0.14.1).

Every setting this server reads from its environment is read here and
nowhere else (tests/test_v0141_compat.py forbids any other environment
read in the package). Each has a new spelling, starting EXEGETE_, and
the earlier one, which is still read until v1.0 (names.SETTINGS); the
settings that never had an earlier spelling have the new one only
(names.NEW_ONLY_SETTINGS, read by update_check, installed_as,
call_seconds, coder_name, the researcher's own coder name,
uses_qualcoder, and the desktop extension's two switches (v0.15.1),
small_toolset_switch and i_use_qualcoder_switch, which read_switch
reads). The one other read here is not a setting: Windows' own
folder, SystemRoot, from which the transition check starts PowerShell
by its full path.

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
in lower case, `lifecycle` read as `full`, a workspace path with `~`
expanded, the two switches compared as "is it 1", the AI coder name
after validate_coder_name), and a blank value counts as unset. The value then used is the raw text of
the spelling chosen, so it behaves exactly as it did before the rename.
"""

import os
import sys
from pathlib import Path
from typing import (Any, Callable, Dict, List, Mapping, NamedTuple, Optional,
                    Tuple)

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
    tidied = value.strip().lower()
    return names.OLD_TOOLSET_NAMES.get(tidied, tidied)


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
    # a read that treats a blank value in its own way goes on doing so (a
    # blank AI coder name means not set, v0.15.0: project_settings).
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


# Three fixed settings for the reading process on Linux (v0.15.1), never
# taken from the host: the address-space limit it sets on itself counts
# what each thread reserves, and PyMuPDF 2.0 loads numpy and onnxruntime,
# so the C library keeps two memory arenas rather than up to eight per
# processor, and numpy's OpenBLAS and any OpenMP pool start one thread.
READER_LINUX_SETTINGS = {"MALLOC_ARENA_MAX": "2",
                         "OPENBLAS_NUM_THREADS": "1",
                         "OMP_NUM_THREADS": "1"}

# One fixed setting for the reading process on every system (v0.15.1),
# never taken from the host: PyMuPDF 2.0 loads onnxruntime as it is
# imported, and onnxruntime's usage reports to Microsoft are on by
# default. On Linux and macOS this stops them before anything is kept or
# sent: no device id or event store in the account's home (where the
# reading process, given no HOME, would find it from the account's own
# entry), no upload. Windows' reports, through the system's event
# tracing, do not read it: the reading process calls onnxruntime's own
# switch before PyMuPDF starts its models
# (import_reading._onnxruntime_reports_off).
READER_SETTINGS = {"ORT_DISABLE_TELEMETRY": "1"}


def reader_process_environment() -> Dict[str, str]:
    """The few variables the document import's reading process is
    started with (0.14.3): the system path, the locale and,
    on Windows, the system root; never the host's other settings. On
    every system, READER_SETTINGS as well, and on Linux
    READER_LINUX_SETTINGS, both fixed here."""
    keep = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "SYSTEMROOT", "SystemRoot")
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env.update(READER_SETTINGS)
    if sys.platform.startswith("linux"):
        env.update(READER_LINUX_SETTINGS)
    return env


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


def installed_as_extension(environ: Optional[Mapping[str, str]] = None
                           ) -> bool:
    """Whether this copy runs as the desktop extension, by its own mark
    (EXEGETE_INSTALLED_AS saying `extension`, spaces and letter case
    aside), as updates.detect_route and the time per import call read
    it."""
    return (installed_as(environ) or "").strip().lower() == "extension"


def call_seconds(environ: Optional[Mapping[str, str]] = None
                 ) -> Optional[str]:
    """EXEGETE_CALL_SECONDS, which has one spelling only (names.
    NEW_ONLY_SETTINGS): its raw value, or None when it is not set.
    doc_import.call_seconds says what each value means."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["call_seconds"])


def coder_name(environ: Optional[Mapping[str, str]] = None
               ) -> Optional[str]:
    """EXEGETE_CODER_NAME, the researcher's own coder name, which has one
    spelling only (names.NEW_ONLY_SETTINGS): its raw value, or None when
    it is not set. project_settings.settings_coder_name says what each
    value means."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["coder_name"])


def uses_qualcoder(environ: Optional[Mapping[str, str]] = None
                   ) -> Optional[str]:
    """EXEGETE_USES_QUALCODER, the answer to "Do you also use QualCoder on
    this computer?", which has one spelling only (names.
    NEW_ONLY_SETTINGS): its raw value, or None when it is not set.
    qualcoder_history.read_setting says what each value means."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["uses_qualcoder"])


# The words that switch a setting on or off (v0.15.1: one list for the
# check for new versions, updates.read_setting, and the extension's two
# switches, read_switch), stripped and in any letter case.
SWITCH_ON = ("on", "true", "1")
SWITCH_OFF = ("off", "false", "0")


def small_toolset_switch(environ: Optional[Mapping[str, str]] = None
                         ) -> Optional[str]:
    """EXEGETE_SMALL_TOOLSET, the extension's switch "Limit Exegete to
    its small tool set", which has one spelling only (names.
    NEW_ONLY_SETTINGS): its raw value, or None when it is not set.
    read_switch says what each value means."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["small_toolset"])


def i_use_qualcoder_switch(environ: Optional[Mapping[str, str]] = None
                           ) -> Optional[str]:
    """EXEGETE_I_USE_QUALCODER, the extension's switch "I use QualCoder on
    this computer", which has one spelling only (names.
    NEW_ONLY_SETTINGS): its raw value, or None when it is not set.
    read_switch says what each value means."""
    env = os.environ if environ is None else environ
    return env.get(names.NEW_ONLY_SETTINGS["i_use_qualcoder"])


def read_switch(raw: Any) -> Tuple[bool, bool]:
    """(on, recognised) for a switch's raw value. Unset, blank, or a
    placeholder the app left unfilled (`${...}`, once stripped) is off,
    recognised; an on word (SWITCH_ON), stripped, in any letter case, is
    on; an off word (SWITCH_OFF) is off; anything else, a value that is
    not text included, is off, not recognised. It never raises."""
    if raw is None:
        return False, True
    if not isinstance(raw, str):
        return False, False
    word = raw.strip().lower()
    if not word or word.startswith("${"):
        return False, True
    if word in SWITCH_ON:
        return True, True
    if word in SWITCH_OFF:
        return False, True
    return False, False


def switch_warnings(environ: Optional[Mapping[str, str]] = None
                    ) -> List[str]:
    """One start-up log line for each switch whose value is not
    recognised, naming the switch and never its value; it is read as off
    and never stops Exegete."""
    readers = (("small_toolset", small_toolset_switch),
               ("i_use_qualcoder", i_use_qualcoder_switch))
    lines = []
    for key, reader in readers:
        _on, recognised = read_switch(reader(environ))
        if not recognised:
            lines.append(
                f"{names.NEW_ONLY_SETTINGS[key]} is not one of on, off, "
                f"true, false, 1 or 0, so it is read as off.")
    return lines


def windows_system_root() -> str:
    """Windows' own folder: SystemRoot, or C:\\Windows when it is unset
    or not a full path (a relative one would be looked up from the
    current folder)."""
    root = os.environ.get("SystemRoot", "")
    return root if os.path.isabs(root) else "C:\\Windows"


# The system's own values that reading a file on the computer needs
# (v0.14.3). Not settings: where this account's caches live,
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


def wsl_distribution() -> bool:
    """Whether WSL (Windows Subsystem for Linux) names the distribution
    this process runs in: WSL_DISTRO_NAME is set. Inside WSL the list of
    running programs holds none of Windows' (v0.15.0)."""
    return bool(os.environ.get("WSL_DISTRO_NAME"))
