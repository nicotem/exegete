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
  nothing is copied: the move never copies or duplicates the key), then
  a link under the old name so that a copy still on 0.14 on the same
  computer uses the same folder: a relative symbolic link on macOS and
  Linux (it survives a home folder carried to another computer or user
  name), a directory junction on Windows (which needs neither Developer
  Mode nor administrator rights, as a symbolic link would).
- The link cannot be made: if something now exists at the old path (an
  older copy wrote there between the rename and the link, or another
  start made the link), both are left as they are, and the folder stays
  moved (that older copy's new folder has a key of its own, which this
  server never uses); otherwise the folder is renamed straight back, and
  the next start tries again.
- The rename fails (a file held open on Windows, permissions): this run
  uses ~/.qualcoder_mcp, nothing is copied, the next start tries again.
- Both exist and the old one is a real folder: only session files the
  new folder lacks are moved (never overwriting); the old key, hint and
  records stay where they are. The log says so once for that folder, not
  at every start (a small note in the new folder remembers it), and
  again only when a later start moves a session file.
- The old path is already a link to the new folder: nothing to do. A
  link there that leads to no folder (most often the one this server
  left, after ~/.exegete was removed by hand) is left as it is, and a
  fresh, empty ~/.exegete is made, which such a link reaches again:
  renamed, it would have become a ~/.exegete that is a link to itself,
  where no key could ever be made. Any other link there is moved as it
  is.
"""

import hashlib
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


def other() -> Path:
    """The one of the two folders this run does not use: ~/.qualcoder_mcp,
    or ~/.exegete in a run whose move could not be made. The guards
    refuse it as well as this run's own, so both are refused in every
    run."""
    return old_path() if _this_run is None else new_path()


def shown() -> str:
    """This run's state folder as a message names it: `~/.exegete`, or
    `~/.qualcoder_mcp` in a run whose move could not be made."""
    return f"~/{current().name}"


def in_this_run(text: str) -> str:
    """A message that points at the state folder, naming the one this
    run uses (it is written naming ~/.exegete)."""
    here = shown()
    usual = f"~/{names.STATE_FOLDER}"
    return text if here == usual else text.replace(usual, here)


# A small note in the new folder that the log has already said the old
# path is a folder of its own (or a link elsewhere), so that the warning
# is not repeated at every start. It holds a digest of what identifies
# that old path (the folder's device and inode, or the link's target),
# never a path or a name; a different old folder is said again.
NOTE_FILE = "old_folder_noted"


def _identity(old: Path) -> Optional[str]:
    try:
        if is_link(old):
            what = "link " + os.readlink(old)
        else:
            st = os.stat(old)
            what = f"folder {st.st_dev} {st.st_ino}"
    except (OSError, ValueError):
        return None
    return hashlib.sha256(
        what.encode("utf-8", "surrogateescape")).hexdigest()


def _already_said(new: Path, old: Path) -> bool:
    identity = _identity(old)
    note = new / NOTE_FILE
    if identity is None or is_link(note):
        return False
    try:
        with open(note, "r", encoding="ascii") as f:
            return f.read(200).strip() == identity
    except (OSError, ValueError):
        return False


def _note_said(new: Path, old: Path) -> bool:
    """Remember that the log has said it; False when it could not be
    written (the next start then says it again)."""
    identity = _identity(old)
    if identity is None:
        return False
    flags = (os.O_WRONLY | os.O_CREAT | os.O_TRUNC
             | getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(new / NOTE_FILE, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as f:
            f.write(identity + "\n")
    except OSError:
        return False
    return True


ONCE = " Later starts do not repeat this."


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


def _leave_a_link_to_nothing(new: Path, old: Path, new_name: str,
                             old_name: str) -> MoveResult:
    """~/.exegete absent and ~/.qualcoder_mcp a link that leads to no
    folder: most often the link this server left, after ~/.exegete was
    removed by hand. Renamed, it would become a ~/.exegete that is a
    link to itself (or to nothing), where no key could ever be made. So
    it is left as it is, and a fresh, empty ~/.exegete is made, owner-only,
    which a link naming it then reaches again. Nothing is moved."""
    try:
        os.mkdir(new, 0o700)
    except OSError:
        pass              # made by another start, or left to the first write
    if os.path.isdir(new) and not is_link(new) and same_folder(old, new):
        return MoveResult(new, "old link led nowhere", (
            f"{old_name} was a link to {new_name}, which did not exist "
            f"(removed by hand?); the link was left as it is, and a fresh, "
            f"empty {new_name} was made, which it reaches again. Nothing "
            f"was moved."))
    said = os.path.isdir(new) and _note_said(new, old)
    return MoveResult(new, "old link led nowhere", (
        f"{old_name} is a link that leads to no folder; it was left as it "
        f"is, nothing was moved, and this server uses a fresh {new_name}."
        + (ONCE if said else "")))


def move(home: Optional[Path] = None,
         windows: Optional[bool] = None) -> MoveResult:
    """Move the old state folder to the new one, once (module docstring).

    Nothing here removes, copies or rewrites a file of the state: a
    folder is renamed (or renamed back), a link is made, an empty folder
    is made, session files the new folder lacks are moved one by one, or
    the small note that a warning was given is written (NOTE_FILE). The
    log lines name no path beyond the two folders' names in the home
    folder.
    """
    new, old = new_path(home), old_path(home)
    new_name, old_name = _names(home)
    if os.path.lexists(new):
        if not os.path.lexists(old):
            return MoveResult(new, "in place", None)
        if is_link(old):
            if same_folder(old, new):
                return MoveResult(new, "linked", None)
            if _already_said(new, old):
                return MoveResult(new, "old path is another link", None)
            return MoveResult(new, "old path is another link", (
                f"{old_name} is a link, but not to {new_name} (to another "
                f"folder, or to none); it was left as it is, and this "
                f"server uses {new_name}."
                + (ONCE if _note_said(new, old) else "")))
        if os.path.isdir(old):
            count = move_missing_sessions(old, new, windows)
            moved = (f"{count} session file(s) {new_name} lacked were moved "
                     f"from {old_name}")
            if _already_said(new, old):
                return MoveResult(new, "both", None if not count else (
                    f"{moved}, where an older copy of the server may still "
                    f"be writing; nothing else there was touched."))
            return MoveResult(new, "both", (
                f"Both {new_name} and {old_name} are folders: an older copy "
                f"of the server, or a restore, may have made the second one, "
                f"and any secret in it is that copy's own, which this server "
                f"does not use. This server uses {new_name}; {moved}, and "
                f"nothing else there was touched or overwritten. INSTALL.md's "
                f"troubleshooting says what to do."
                + (ONCE if _note_said(new, old) else "")))
        return MoveResult(new, "old path is not a folder", None)
    if not os.path.lexists(old):
        return MoveResult(new, "fresh", None)
    if is_link(old) and not os.path.isdir(old):
        return _leave_a_link_to_nothing(new, old, new_name, old_name)
    if not os.path.isdir(old):
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
