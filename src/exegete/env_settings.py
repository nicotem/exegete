# SPDX-License-Identifier: LGPL-3.0-or-later
"""The server's settings, read under both spellings (v0.14.1).

Every setting this server reads from its environment is read here and
nowhere else (tests/test_v0141_compat.py forbids any other environment
read in the package). Each has a new spelling, starting EXEGETE_, and
the earlier one, which is still read until v1.0 (names.SETTINGS).

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
