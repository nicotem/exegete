# SPDX-License-Identifier: LGPL-3.0-or-later
"""The state folder, and its one move from ~/.qualcoder_mcp (v0.14.1).

The state folder holds the preview-token key (which also seals every
pseudonymisation run record), the AI coding sessions awaiting review,
the last-project hint and the run records. It was ~/.qualcoder_mcp and
is ~/.exegete from 0.14.1 (PROVISIONAL: decision 6).

`move` runs once per real start, from `main()` only (never at import,
never for --version), after every start-up refusal:

- ~/.exegete absent and ~/.qualcoder_mcp a folder: ONE `os.rename` of
  the whole folder (the same volume, so it is atomic, modes are kept and
  nothing is copied: there is never a second key), then a link under the
  old name so that a copy still on 0.14 on the same computer uses the
  same folder: a relative symbolic link on macOS and Linux (it survives
  a home folder carried to another computer or user name), a directory
  junction on Windows (which needs neither Developer Mode nor
  administrator rights, as a symbolic link would).
- The link cannot be made: if something now exists at the old path (an
  older copy wrote there between the rename and the link, or another
  start made the link), both are left as they are; otherwise the folder
  is renamed straight back, and the next start tries again. So the
  folder never stays moved without a link.
- The rename fails (a file held open on Windows, permissions): this run
  uses ~/.qualcoder_mcp, nothing is copied, the next start tries again.
- Both exist and the old one is a real folder: only session files the
  new folder lacks are moved (never overwriting); the old key, hint and
  records stay where they are.
- The old path is already a link to the new folder: nothing to do. Any
  other link there is moved as it is.
"""

import os
import subprocess
from pathlib import Path
from typing import NamedTuple, Optional

from . import names

# The folder chosen for this run when the move could not be made (the
# old one), or None: the new one.
_this_run: Optional[Path] = None


class MoveResult(NamedTuple):
    """Where this run keeps its state, what happened, and the one log
    line to write (None when there is nothing to say)."""
    state_home: Path
    outcome: str
    message: Optional[str]


def new_path(home: Optional[Path] = None) -> Path:
    return Path(home if home is not None else Path.home()) / \
        names.STATE_FOLDER


def old_path(home: Optional[Path] = None) -> Path:
    return Path(home if home is not None else Path.home()) / \
        names.OLD_STATE_FOLDER


def current() -> Path:
    """The state folder for this run: the new one, unless the move
    failed at this run's start."""
    return _this_run if _this_run is not None else new_path()


def use_for_this_run(path: Optional[Path]) -> None:
    global _this_run
    _this_run = None if path is None else Path(path)


def is_link(path: Path) -> bool:
    """A symbolic link, or on Windows a junction (or another reparse
    point), rather than a real folder."""
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)     # Python 3.12
    if isjunction is not None and isjunction(path):
        return True
    if os.name == "nt":
        try:
            attributes = getattr(os.lstat(path), "st_file_attributes", 0)
        except OSError:
            return False
        return bool(attributes & 0x400)       # FILE_ATTRIBUTE_REPARSE_POINT
    return False


def same_folder(first: Path, second: Path) -> bool:
    try:
        return os.path.normcase(os.path.realpath(first)) == \
            os.path.normcase(os.path.realpath(second))
    except (OSError, ValueError):
        return False


def _make_junction(target: Path, link: Path) -> None:
    """A directory junction at `link` to `target` (absolute, as a
    junction must be): CPython's own `_winapi.CreateJunction`, which it
    has but does not document, else `mklink /J`."""
    try:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        return
    except (ImportError, AttributeError):
        pass
    except OSError:
        if os.path.lexists(link):
            raise
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link),
                             str(target)], capture_output=True)
    if result.returncode != 0 or not os.path.lexists(link):
        raise OSError(f"mklink /J failed ({result.returncode})")


def make_link(new: Path, old: Path, windows: Optional[bool] = None) -> None:
    """The link under the old name, pointing at the new folder."""
    windows = (os.name == "nt") if windows is None else windows
    if windows:
        _make_junction(new, old)
    else:
        # Relative: `.exegete`, beside the link, in the home folder
        os.symlink(new.name, str(old), target_is_directory=True)


def move_missing_sessions(old: Path, new: Path,
                          windows: Optional[bool] = None) -> int:
    """Move the session files the new folder lacks from the old one;
    never overwrite one. How many were moved."""
    windows = (os.name == "nt") if windows is None else windows
    source = old / "sessions"
    target = new / "sessions"
    if not source.is_dir() or is_link(source):
        return 0
    moved = 0
    for path in sorted(source.glob("session_*.json")):
        if is_link(path) or not path.is_file():
            continue
        destination = target / path.name
        if os.path.lexists(destination):
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            if windows:
                os.rename(path, destination)   # refuses an existing target
            else:
                os.link(path, destination)     # refuses an existing target
                os.unlink(path)
        except OSError:
            continue
        moved += 1
    return moved


def _names(home: Optional[Path]):
    return (f"~/{names.STATE_FOLDER}", f"~/{names.OLD_STATE_FOLDER}")


def move(home: Optional[Path] = None,
         windows: Optional[bool] = None) -> MoveResult:
    """Move the old state folder to the new one, once (module docstring).

    Nothing here removes, copies or rewrites a file: a folder is renamed
    (or renamed back), a link is made, or session files the new folder
    lacks are moved one by one. The log lines name no path beyond the two
    folders' names in the home folder.
    """
    new, old = new_path(home), old_path(home)
    new_name, old_name = _names(home)
    if os.path.lexists(new):
        if not os.path.lexists(old):
            return MoveResult(new, "in place", None)
        if is_link(old):
            if same_folder(old, new):
                return MoveResult(new, "linked", None)
            return MoveResult(new, "old path is another link", (
                f"{old_name} is a link to another folder, not to "
                f"{new_name}; it was left as it is, and this server uses "
                f"{new_name}."))
        if os.path.isdir(old):
            count = move_missing_sessions(old, new, windows)
            return MoveResult(new, "both", (
                f"Both {new_name} and {old_name} exist (an older copy of the "
                f"server may have made the second one). This server uses "
                f"{new_name}; {count} session file(s) it lacked were moved "
                f"from {old_name}, and nothing else there was touched or "
                f"overwritten."))
        return MoveResult(new, "old path is not a folder", None)
    if not os.path.lexists(old):
        return MoveResult(new, "fresh", None)
    if not (os.path.isdir(old) or is_link(old)):
        return MoveResult(new, "old path is not a folder", None)
    try:
        os.rename(old, new)
    except OSError as error:
        if os.path.isdir(new) and (not os.path.lexists(old)
                                   or same_folder(old, new)):
            # Another start moved it a moment ago
            return MoveResult(new, "moved by another start", None)
        use_old = f"{old_name} could not be renamed to {new_name}"
        return MoveResult(old, "rename failed", (
            f"{use_old} ({type(error).__name__}); this run uses "
            f"{old_name} as before, nothing was copied, and the next start "
            f"tries again."))
    try:
        make_link(new, old, windows)
    except OSError as error:
        if os.path.lexists(old):
            if is_link(old) and same_folder(old, new):
                return MoveResult(new, "moved", None)
            return MoveResult(new, "moved, old path taken", (
                f"The state folder was moved to {new_name}, but something "
                f"was written to {old_name} before the link could be made "
                f"(an older copy of the server?). Both are kept and nothing "
                f"was overwritten; the next start moves the session files "
                f"{new_name} lacks."))
        try:
            os.rename(new, old)
        except OSError:
            return MoveResult(new, "moved, no link", (
                f"The state folder was moved to {new_name}, but neither a "
                f"link under {old_name} could be made ({type(error).__name__}) "
                f"nor the folder put back. This server uses {new_name}; an "
                f"older copy of the server would not find it."))
        return MoveResult(old, "link failed, put back", (
            f"A link under {old_name} could not be made "
            f"({type(error).__name__}), so the state folder was put back "
            f"there; this run uses {old_name}, and the next start tries "
            f"again."))
    return MoveResult(new, "moved", (
        f"The state folder was moved from {old_name} to {new_name}, whole, "
        f"and a link was left under the old name for older copies of the "
        f"server."))
