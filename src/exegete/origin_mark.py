# SPDX-License-Identifier: LGPL-3.0-or-later
"""The mark a system puts on a file that came from the internet, carried
from one file to its copy (v0.14.3).

Word opens a document marked as from the internet in Protected View,
read-only and without fetching the pictures or templates it links to;
macOS asks before an app opens a marked file for the first time. The
mark lives beside the bytes, not in them, so a plain copy loses it:

- on a Mac, the extended attribute `com.apple.quarantine`;
- on Windows, the alternate data stream `Zone.Identifier`.

`carry(source, copy)` gives the copy the source's mark, if it has one,
and never invents one: marking every copy would put Word's warning bar
over the researcher's own files (the import and reading design, Part
3). Linux has no such mark, so nothing is done there. The mark is
metadata only: the copy's bytes are the source's. A failure to carry it
is reported, not raised, since the copy is still a faithful copy.
"""

import ctypes
import ctypes.util
import sys
from pathlib import Path
from typing import Optional

MAC_ATTRIBUTE = b"com.apple.quarantine"
WINDOWS_STREAM = "Zone.Identifier"

# getxattr/setxattr options on macOS: do not follow a link.
_XATTR_NOFOLLOW = 0x0001
_MAX_MARK = 4096          # a quarantine value is a short line of text


def _libc():
    return ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def _mac_read(path: Path) -> Optional[bytes]:
    libc = _libc()
    libc.getxattr.restype = ctypes.c_ssize_t
    libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p,
                              ctypes.c_void_p, ctypes.c_size_t,
                              ctypes.c_uint32, ctypes.c_int]
    buffer = ctypes.create_string_buffer(_MAX_MARK)
    size = libc.getxattr(bytes(path), MAC_ATTRIBUTE, buffer, _MAX_MARK, 0,
                         _XATTR_NOFOLLOW)
    if size < 0:
        return None
    return buffer.raw[:size]


def _mac_write(path: Path, value: bytes) -> bool:
    libc = _libc()
    libc.setxattr.restype = ctypes.c_int
    libc.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p,
                              ctypes.c_void_p, ctypes.c_size_t,
                              ctypes.c_uint32, ctypes.c_int]
    return libc.setxattr(bytes(path), MAC_ATTRIBUTE, value, len(value), 0,
                         _XATTR_NOFOLLOW) == 0


def _windows_read(path: Path) -> Optional[bytes]:
    try:
        with open(f"{path}:{WINDOWS_STREAM}", "rb") as stream:
            return stream.read(_MAX_MARK)
    except OSError:
        return None


def _windows_write(path: Path, value: bytes) -> bool:
    try:
        with open(f"{path}:{WINDOWS_STREAM}", "wb") as stream:
            stream.write(value)
        return True
    except OSError:
        return False


def read(path, platform: Optional[str] = None) -> Optional[bytes]:
    """The file's internet-origin mark, or None when it has none."""
    platform = platform or sys.platform
    path = Path(path)
    if platform == "darwin":
        return _mac_read(path)
    if platform == "win32":
        return _windows_read(path)
    return None


def write(path, value: bytes, platform: Optional[str] = None) -> bool:
    """Put `value` on the file as its internet-origin mark."""
    platform = platform or sys.platform
    path = Path(path)
    if platform == "darwin":
        return _mac_write(path, value)
    if platform == "win32":
        return _windows_write(path, value)
    return False


def carry(source, copy, platform: Optional[str] = None) -> Optional[bool]:
    """Give `copy` the mark `source` has. None when the source has none
    (nothing to carry), True when carried, False when it could not be.
    Call it before the copy is made read-only."""
    value = read(source, platform)
    if value is None:
        return None
    return write(copy, value, platform)
