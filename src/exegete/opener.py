# SPDX-License-Identifier: LGPL-3.0-or-later
"""Asking the system to open a file in its own app, or to show it in its
folder (v0.14.3; the import and reading design, Part 7).

Opening a file is launching a program by another name, so the rules are
narrow:

- only a file Exegete has just written into its own reading folder is
  ever opened or shown (the caller checks that; `open_file` and
  `show_in_folder` check it again);
- never a shell: each call is a list of arguments, with the program's
  full path where the system fixes one, the file's absolute path (so a
  name starting with `-` is never read as an option), a time limit, and
  a failure reported, not retried;
- never Python's `webbrowser` module (on Windows it starts whatever it is
  given, on a Mac it puts the path inside an AppleScript), and never
  `qlmanage` (Apple calls it a debugging tool; Finder's own Quick Look,
  the space bar on a file Finder shows, is the native route);
- only the document and media types QualCoder imports are opened, and
  Exegete's own pages; a web page that was a project's original is only
  shown in its folder, since a browser would run its scripts; anything
  else is only shown;
- no screen, no opening: in an SSH session, or on Linux with neither
  DISPLAY nor WAYLAND_DISPLAY, nothing is opened and the answer gives the
  location.

The calls, by system:

| | open in its own app | show in its folder |
|---|---|---|
| macOS | /usr/bin/open PATH | /usr/bin/open -R PATH |
| Windows | os.startfile(PATH) | SHOpenFolderAndSelectItems, in a child process with a time limit |
| Linux | xdg-open PATH | the file manager's D-Bus ShowItems, else xdg-open on the folder |
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

from . import env_settings

# The document and media types QualCoder imports (the design's list).
OPENABLE = frozenset({
    ".docx", ".odt", ".rtf", ".txt", ".md", ".pdf", ".epub", ".srt",
    ".vtt", ".jpg", ".jpeg", ".png", ".flac", ".m4a", ".mp3", ".ogg",
    ".wav", ".mkv", ".mov", ".mp4", ".m4v", ".wmv", ".webm",
})
# Web pages: Exegete's own reading pages are opened; an original that is
# a web page is only shown.
WEB_PAGES = frozenset({".htm", ".html"})

TIME_LIMIT = 15          # seconds for a launcher to hand over

# Run in a child Python with its own isolation flag: the path arrives as
# an argument, never inside the code.
_WINDOWS_SELECT = (
    "import ctypes,sys\n"
    "from ctypes import wintypes\n"
    "ole32=ctypes.windll.ole32;shell32=ctypes.windll.shell32\n"
    "ole32.CoInitialize(None)\n"
    "shell32.ILCreateFromPathW.restype=ctypes.c_void_p\n"
    "shell32.ILCreateFromPathW.argtypes=[wintypes.LPCWSTR]\n"
    "shell32.SHOpenFolderAndSelectItems.argtypes="
    "[ctypes.c_void_p,wintypes.UINT,ctypes.c_void_p,wintypes.DWORD]\n"
    "shell32.ILFree.argtypes=[ctypes.c_void_p]\n"
    "p=shell32.ILCreateFromPathW(sys.argv[1])\n"
    "if not p: sys.exit(2)\n"
    "r=shell32.SHOpenFolderAndSelectItems(p,0,None,0)\n"
    "shell32.ILFree(p)\n"
    "sys.exit(0 if r==0 else 3)\n"
)


class Outcome(NamedTuple):
    """What happened: whether the system was asked and accepted, and,
    when not, why, in plain words."""
    done: bool
    reason: Optional[str] = None


def screen(platform: Optional[str] = None) -> Optional[str]:
    """None when a window can be opened here, else why not."""
    platform = platform or sys.platform
    if env_settings.remote_session():
        return ("Exegete runs in an SSH session here, so a window would "
                "not open on your screen")
    if platform not in ("darwin", "win32") and \
            not env_settings.linux_display():
        return "this computer has no desktop session for a window"
    return None


def run_launcher(argv: List[str]) -> int:
    """Run a launcher with no shell and a time limit; its exit code, or
    -1 when it could not be started or took too long."""
    try:
        completed = subprocess.run(
            argv, shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=TIME_LIMIT, close_fds=True)
    except (OSError, subprocess.SubprocessError, ValueError):
        return -1
    return completed.returncode


# The launcher every call goes through (the test suite replaces it with
# a recorder, so that no test opens a window).
_run = run_launcher


def _startfile(path: str) -> bool:
    """Windows' own way to open a document in its app."""
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except (OSError, AttributeError):
        return False
    return True


def _which(name: str) -> Optional[str]:
    found = shutil.which(name)
    return found if found and os.path.isabs(found) else None


def _check(path: Path) -> Optional[str]:
    """The path must be absolute, inside Exegete's reading folder, and
    name an existing ordinary file."""
    from . import reading_folder
    from .path_identity import is_inside
    if not path.is_absolute():
        return "the file's place is not a full path"
    if path.is_symlink() or not path.is_file():
        return "the file is not there as an ordinary file"
    if not is_inside(path, reading_folder.root()):
        return "Exegete opens only files in its own reading folder"
    return None


def openable(path: Path, own_page: bool) -> bool:
    """Whether a file of this type is opened, not only shown."""
    suffix = path.suffix.lower()
    if suffix in WEB_PAGES:
        return own_page
    return suffix in OPENABLE


def open_file(path, own_page: bool = False,
              platform: Optional[str] = None) -> Outcome:
    """Ask the system to open `path` in the app it uses for that type."""
    platform = platform or sys.platform
    path = Path(path)
    problem = _check(path) or screen(platform)
    if problem:
        return Outcome(False, problem)
    if not openable(path, own_page):
        return Outcome(False, "files of this type are only shown in their "
                              "folder, never opened by Exegete")
    target = str(path)
    if platform == "darwin":
        ok = _run(["/usr/bin/open", target]) == 0
    elif platform == "win32":
        ok = _startfile(target)
    else:
        launcher = _which("xdg-open")
        ok = launcher is not None and _run([launcher, target]) == 0
    return Outcome(True) if ok else Outcome(
        False, "the system did not open it")


def show_in_folder(path, platform: Optional[str] = None) -> Outcome:
    """Ask the system's file manager to show `path` selected in its
    folder (on a Mac, the space bar then gives Quick Look)."""
    platform = platform or sys.platform
    path = Path(path)
    problem = _check(path) or screen(platform)
    if problem:
        return Outcome(False, problem)
    target = str(path)
    if platform == "darwin":
        ok = _run(["/usr/bin/open", "-R", target]) == 0
    elif platform == "win32":
        ok = _run([sys.executable, "-I", "-S", "-c", _WINDOWS_SELECT,
                   target]) == 0
    else:
        ok = _linux_show(path)
    return Outcome(True) if ok else Outcome(
        False, "the system did not show it")


def _linux_show(path: Path) -> bool:
    """The freedesktop file manager's ShowItems over D-Bus, with the
    file's address fully percent-encoded (so a comma in a name cannot
    split dbus-send's list); else the folder opened with xdg-open."""
    uri = path.as_uri()
    sender = _which("dbus-send")
    if sender is not None and _run([
            sender, "--session", "--print-reply",
            "--dest=org.freedesktop.FileManager1", "--type=method_call",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1.ShowItems",
            f"array:string:{uri}", "string:"]) == 0:
        return True
    launcher = _which("xdg-open")
    return launcher is not None and _run([launcher, str(path.parent)]) == 0
