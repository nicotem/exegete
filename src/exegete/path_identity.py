# SPDX-License-Identifier: LGPL-3.0-or-later
"""Whether a path lies inside a folder, decided by which folder it really
is (0.14.3, provisional).

Comparing paths as text misses the same folder spelt another way. On a
Mac's usual disk, and on Windows, letter case is ignored, so
`~/documents/exegete projects/Pilot.qda` is the project folder
`~/Documents/Exegete projects/Pilot.qda`, and a textual check lets a
write into it through. `Path.resolve()` follows links but keeps the
letter case it is given on macOS, so resolving first does not help.

So the check here compares each existing folder on the way with the
given folder by identity: its device and its file number (`st_dev`,
`st_ino`), which two spellings of one folder share and two folders never
do. The textual comparison is kept as well, for a path whose folders do
not exist yet and for file systems that report no file numbers.

One check for every tool that refuses a place: the export tools'
refusals of the project and state folders, and the document import's
refusals of the project, the state folder and the reading folder.
"""

import os
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

PathLike = Union[str, "os.PathLike[str]"]


def _identity(path: PathLike) -> Optional[Tuple[int, int]]:
    """(device, file number) of an existing path, following links, or
    None when it cannot be read or the file system gives no file
    number."""
    try:
        info = os.stat(path)
    except (OSError, ValueError):
        return None
    if not info.st_ino:
        return None
    return (info.st_dev, info.st_ino)


def _spelt_inside(path: Path, folder: Path) -> bool:
    """The textual comparison, with Windows' own case folding."""
    def norm(p: Path) -> str:
        return os.path.normcase(str(p))
    target = norm(path)
    top = norm(folder)
    if target == top:
        return True
    return any(norm(parent) == top for parent in path.parents)


def is_inside(path: PathLike, folder: Optional[PathLike]) -> bool:
    """Whether `path` is `folder` or lies inside it.

    Both are resolved first (links followed, `..` collapsed); then the
    path and each of its existing parents is compared with the folder by
    identity, and the spellings are compared as well. A folder that does
    not exist contains only what is spelt inside it.
    """
    if folder is None:
        return False
    try:
        target = Path(path).expanduser().resolve()
        top = Path(folder).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    if _spelt_inside(target, top):
        return True
    wanted = _identity(top)
    if wanted is None:
        return False
    for part in (target,) + tuple(target.parents):
        if _identity(part) == wanted:
            return True
    return False


def is_inside_any(path: PathLike,
                  folders: Iterable[Optional[PathLike]]) -> bool:
    """Whether `path` lies inside any of `folders`."""
    return any(is_inside(path, folder) for folder in folders)
