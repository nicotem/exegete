# SPDX-License-Identifier: LGPL-3.0-or-later
"""Where documents may be imported from (0.14.3; the
design's Part 3, "Where imports may come from").

A path is walked step by step from its root, and each step is judged by
its own marks, read without following it:

- a link (a symbolic link, a Windows junction or mount point) is refused,
  except a link among the given path's folders that lands inside a Mac
  cloud drive's folder (`~/OneDrive - University of Exeter` is one);
  a link as the file itself, or among a folder's entries, is always
  refused. A cloud drive's placeholder for a file kept online only is
  not a link;
- a hidden place is refused: a name starting with a dot; on a Mac the
  system's hidden flag (which `~/Library` carries), except the cloud
  drives' own folders under `~/Library`; on Windows the hidden or system
  mark (which `AppData` carries). The system's own top folders a Mac
  hides for tidiness (`/Volumes`, where drives and shares are mounted,
  and `/private`) and a drive's root are not judged; a Mac's own links
  at the top of the disk (`/tmp`, `/var`, `/etc`) are read as the
  folders they name;
- a network path typed as such (two slashes or backslashes first, as in
  `//server/share`, and their long forms) is refused: reaching one makes
  Windows offer the account's credentials to the computer it names. A
  drive letter the system has mapped, and a share mounted under
  `/Volumes`, are accepted;
- the open project's folder, Exegete's state folders and its reading
  folder are refused, decided by which folder each is (path_identity),
  never by comparing paths as text.

Nothing here reads a file's contents; the import does that, once, after
these checks.
"""

import os
import stat
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .path_identity import is_inside

MAX_FOLDER_ENTRIES = 10_000

# Windows' marks (stat.FILE_ATTRIBUTE_*), spelt out so the module reads
# the same on every system.
_FILE_ATTRIBUTE_HIDDEN = 0x2
_FILE_ATTRIBUTE_SYSTEM = 0x4
_IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
_IO_REPARSE_TAG_SYMLINK = 0xA000000C
_UF_HIDDEN = getattr(stat, "UF_HIDDEN", 0x8000)

# A Mac's own links at the top of the disk, read as the folders they name.
_MAC_SYSTEM_LINKS = {"/tmp": "/private/tmp", "/var": "/private/var",
                     "/etc": "/private/etc"}
_MAC_UNJUDGED_TOP = frozenset({"/Volumes", "/private"})


class PathRefused(Exception):
    """A path the import will not take, with Exegete's own reason code."""

    def __init__(self, code: str, place: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.place = place


@dataclass
class Walked:
    """A path that passed the walk: the place to open, and the real
    place when a link into a cloud folder was followed."""
    path: Path
    is_folder: bool
    real_place: Optional[str] = None


def clean_given(given: str) -> str:
    """A path as the researcher may paste it: surrounding white space and
    one pair of quotes (Windows' "Copy as path" adds them) removed."""
    text = given.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


def is_network_form(text: str) -> bool:
    """Two slashes or backslashes first: a network path, or a long form
    of one."""
    return len(text) >= 2 and text[0] in "/\\" and text[1] in "/\\"


def is_local_long_form(text: str) -> bool:
    """Windows' long form of a path on a drive of this computer
    (\\\\?\\C:\\... or \\\\.\\C:\\...), which is not a network path,
    though it starts with two backslashes."""
    return (len(text) >= 7 and is_network_form(text) and text[2] in "?."
            and text[3] in "/\\" and text[4].isascii()
            and text[4].isalpha() and text[5] == ":"
            and text[6] in "/\\")


def cloud_roots(home: Optional[Path] = None) -> List[Path]:
    """The cloud drives' own folders on a Mac, under `~/Library`."""
    if sys.platform != "darwin":
        return []
    home = Path(home) if home is not None else Path.home()
    return [home / "Library" / "CloudStorage",
            home / "Library" / "Mobile Documents"]


def _is_link(info: os.stat_result) -> bool:
    if stat.S_ISLNK(info.st_mode):
        return True
    tag = getattr(info, "st_reparse_tag", 0)
    return tag in (_IO_REPARSE_TAG_MOUNT_POINT, _IO_REPARSE_TAG_SYMLINK)


def _hidden_by_mark(info: os.stat_result) -> bool:
    if os.name == "nt":
        attributes = getattr(info, "st_file_attributes", 0)
        return bool(attributes & (_FILE_ATTRIBUTE_HIDDEN
                                  | _FILE_ATTRIBUTE_SYSTEM))
    if sys.platform == "darwin":
        return bool(getattr(info, "st_flags", 0) & _UF_HIDDEN)
    return False


def hidden_step(step: Path, info: os.stat_result) -> bool:
    """Whether one step of a path carries the system's hidden mark. One
    function, so the test suite can excuse its own scratch folders,
    which on Windows lie under the hidden AppData."""
    return _hidden_by_mark(info)


def is_hidden_entry(name: str, info: os.stat_result) -> bool:
    return name.startswith(".") or _hidden_by_mark(info)


def _excused_on_a_mac(step: Path, whole: Path, clouds: Sequence[Path]) -> bool:
    """A Mac's hidden flag that does not make a place hidden: the top
    system folders, and `~/Library` on the way into a cloud folder, and
    anything inside one."""
    if str(step) in _MAC_UNJUDGED_TOP:
        return True
    for cloud in clouds:
        if is_inside(step, cloud):
            return True
        if is_inside(whole, cloud) and is_inside(cloud, step):
            return True
    return False


def _refusal_for_unreadable(error: OSError) -> PathRefused:
    if isinstance(error, PermissionError):
        return PathRefused("macos_permission" if sys.platform == "darwin"
                           else "permission")
    if isinstance(error, (FileNotFoundError, NotADirectoryError)):
        return PathRefused("missing")
    return PathRefused("unreadable")


def walk(given: str, refused_places: Sequence[Tuple[str, Optional[Path]]] = (),
         home: Optional[Path] = None) -> Walked:
    """Walk one given path under the rules above, or raise PathRefused.

    `refused_places` pairs a reason code with a folder ("project",
    "state_folder", "reading_folder"); a path inside one is refused with
    that code."""
    text = clean_given(given) if isinstance(given, str) else ""
    if not text or "\x00" in text:
        raise PathRefused("missing")
    if is_local_long_form(text):
        raise PathRefused("long_form")
    if is_network_form(text):
        raise PathRefused("network")
    whole = Path(os.path.expanduser(text))
    if not whole.is_absolute():
        raise PathRefused("relative")
    if any(part == ".." for part in whole.parts):
        raise PathRefused("relative")
    if sys.platform == "darwin":
        for link, real in _MAC_SYSTEM_LINKS.items():
            if str(whole) == link or str(whole).startswith(link + "/"):
                whole = Path(real + str(whole)[len(link):])
                break
    clouds = cloud_roots(home)
    parts = whole.parts
    current = Path(parts[0])
    real_place = None
    remaining = [p for p in parts[1:] if p not in ("", ".")]
    info = None
    while remaining:
        name = remaining.pop(0)
        step = current / name
        try:
            info = os.lstat(step)
        except OSError as error:
            raise _refusal_for_unreadable(error) from None
        if _is_link(info):
            if not remaining:
                raise PathRefused("link")
            target = Path(os.path.realpath(step))
            if not any(is_inside(target, cloud) for cloud in clouds):
                raise PathRefused("link")
            current = target
            whole = target.joinpath(*remaining)
            real_place = str(whole)
            try:
                info = os.stat(target)
            except OSError as error:
                raise _refusal_for_unreadable(error) from None
            continue
        if name.startswith("."):
            raise PathRefused("hidden")
        if hidden_step(step, info) and not (
                sys.platform == "darwin"
                and _excused_on_a_mac(step, whole, clouds)):
            raise PathRefused("hidden")
        current = step
    if info is None:
        raise PathRefused("not_a_file")
    for code, place in refused_places:
        if place is not None and is_inside(current, place):
            raise PathRefused(code)
    if stat.S_ISDIR(info.st_mode):
        return Walked(current, True, real_place)
    if stat.S_ISREG(info.st_mode):
        return Walked(current, False, real_place)
    raise PathRefused("not_a_file")


@dataclass
class FolderListing:
    """What a folder holds that the import can say anything about."""
    files: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    not_files: List[str] = field(default_factory=list)
    other_formats: List[str] = field(default_factory=list)
    subfolders: List[Tuple[str, int]] = field(default_factory=list)
    hidden_skipped: int = 0
    unsupported: int = 0
    looked_at: int = 0
    stopped_early: bool = False


def name_order(name: str):
    folded = unicodedata.normalize("NFC", name)
    return (folded.casefold(), folded)


def _count_supported(folder: str, supported: set, budget: List[int]) -> int:
    count = 0
    try:
        with os.scandir(folder) as inner:
            for item in inner:
                if budget[0] <= 0:
                    break
                budget[0] -= 1
                try:
                    info = item.stat(follow_symlinks=False)
                except OSError:
                    continue
                if (stat.S_ISREG(info.st_mode)
                        and not is_hidden_entry(item.name, info)
                        and os.path.splitext(item.name)[1].lower()
                        in supported):
                    count += 1
    except OSError:
        pass
    return count


def list_folder(folder: Path, supported: Iterable[str],
                known_other: Iterable[str] = ()) -> FolderListing:
    """The folder's own entries, in name order, at most
    MAX_FOLDER_ENTRIES looked at (each subfolder's entries included,
    since its supported files are counted)."""
    supported = {s.lower() for s in supported}
    known_other = {s.lower() for s in known_other}
    listing = FolderListing()
    try:
        with os.scandir(folder) as scan:
            entries = sorted(scan, key=lambda e: name_order(e.name))
    except OSError as error:
        raise _refusal_for_unreadable(error) from None
    budget = [MAX_FOLDER_ENTRIES]
    for entry in entries:
        if budget[0] <= 0:
            listing.stopped_early = True
            break
        budget[0] -= 1
        listing.looked_at += 1
        try:
            info = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        suffix = os.path.splitext(entry.name)[1].lower()
        if is_hidden_entry(entry.name, info):
            listing.hidden_skipped += 1
            continue
        if _is_link(info):
            if suffix in supported:
                listing.links.append(entry.name)
            continue
        if stat.S_ISDIR(info.st_mode):
            listing.subfolders.append(
                (entry.name, _count_supported(entry.path, supported, budget)))
            if budget[0] <= 0:
                listing.stopped_early = True
            continue
        if suffix in supported:
            if stat.S_ISREG(info.st_mode):
                listing.files.append(entry.name)
            else:
                listing.not_files.append(entry.name)
        elif suffix in known_other and stat.S_ISREG(info.st_mode):
            listing.other_formats.append(entry.name)
        else:
            listing.unsupported += 1
    return listing
