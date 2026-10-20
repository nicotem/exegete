# SPDX-License-Identifier: LGPL-3.0-or-later
"""What kind of entry sits at a name in a project (v0.15.1).

A project folder is the researcher's, and an entry in it can be
anything the system allows: a named pipe, a socket, a device, a folder
or a link where a program expects an ordinary file. Opening a named
pipe for reading waits until another program opens it for writing,
which may be never, so a tool that opened one without looking would
never answer. Exegete therefore looks first, by the entry's metadata
alone, at the two places in a project it opens without choosing to:
the lock file and SQLite's side files beside `data.qda`. Neither look
opens, writes, moves or removes anything.

The other readers of project files (the names list, `pseudonyms.json`,
`exegete.json`, the kept texts, the import's chosen files, the originals
read for reading) already refuse such entries by their own `lstat` and
are left as they are.
"""

import os
import stat
from typing import Optional, Union

PathLike = Union[str, "os.PathLike[str]"]

ORDINARY_FILE = "an ordinary file"
NOT_AN_ORDINARY_FILE = "not an ordinary file"


class ProjectFileKindError(ValueError):
    """An entry in a project is not the ordinary file Exegete expects at
    its name: refused before anything opens it. A ValueError, so the
    tool guard answers its words, which name no path."""


def kind_word(mode: int) -> str:
    """The kind of a non-regular entry, in the words a refusal uses:
    "a named pipe", "a socket", "a device", "a folder", "a link", or
    "not an ordinary file" for any other kind."""
    if stat.S_ISFIFO(mode):
        return "a named pipe"
    if stat.S_ISSOCK(mode):
        return "a socket"
    if stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
        return "a device"
    if stat.S_ISDIR(mode):
        return "a folder"
    if stat.S_ISLNK(mode):
        return "a link"
    return NOT_AN_ORDINARY_FILE


def is_kind(kind: str) -> str:
    """"is a named pipe, not an ordinary file", or "is not an ordinary
    file" for the kind that has no name of its own."""
    if kind == NOT_AN_ORDINARY_FILE:
        return f"is {kind}"
    return f"is {kind}, not {ORDINARY_FILE}"


def odd_kind(path: PathLike, follow: bool = False) -> Optional[str]:
    """The kind of the entry at `path` when it is not a regular file;
    None when it is one, or when nothing is there.

    By `lstat`, so a link is "a link"; with `follow`, by `stat`, so a
    link is read through and one that leads nowhere is nothing there.
    An entry the system will not describe counts as nothing there, as
    `os.path.exists` counts it: whoever opens it next meets the
    system's own refusal."""
    try:
        info = os.stat(path) if follow else os.lstat(path)
    except (OSError, ValueError):
        return None
    if stat.S_ISREG(info.st_mode):
        return None
    return kind_word(info.st_mode)


def nonblocking_opener(path: PathLike, flags: int) -> int:
    """An opener for `open()` that never waits on a named pipe: it adds
    O_NONBLOCK where the system has it (not on Windows, which has no
    named pipes in a folder). On a regular file the flag changes
    nothing; the caller reads only once `fstat` of the opened file says
    regular."""
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))
