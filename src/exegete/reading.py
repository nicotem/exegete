# SPDX-License-Identifier: LGPL-3.0-or-later
"""What the reading tool does, native first (v0.14.3, provisional; the
import and reading design, Part 7):

1. `in_folder`: a read-only copy of the original shown in Finder or File
   Explorer (on a Mac, the space bar then gives Quick Look);
2. `original`: that copy opened in its own app (Word, Pages,
   LibreOffice, Preview, a media player): QualCoder's "View original
   text file" (`manage_files.py` 1424-1439 at 9bddf17), done on a copy;
3. `reading_copy`, the default and the one view of Exegete's own: a web
   page with the whole text and its codings, opened in the researcher's
   browser.

Nothing in the project changes, so there is no preview, backup or lock,
and like Exegete's other reads it works while QualCoder has the project
open. Only files Exegete has just written into its reading folder are
opened or shown. The original's copy is made from the stored path,
never from the file's current name (`rename_file` keeps the stored
original under its first name), after the stored name has passed
Exegete's own name rules (a project QualCoder made never passed them)
and the file has been found, by identity, inside the project's folder
for that kind of file, as an ordinary file and not a link. Linked
originals (QualCoder's `docs:` and like paths) are never opened: they
lie outside the project.

The answer gives where the page or copy is, and counts; never the text,
never a memo.
"""

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import opener, reading_copy, reading_folder
from .database import file_name_problem
from .path_identity import is_inside

SHOW_CHOICES = ("reading_copy", "original", "in_folder")

# The project's folders of originals, by the stored path's prefix
# (QualCoder's convention; database._detect_file_type).
STORED_FOLDERS = {"/docs/": "documents", "/images/": "images",
                  "/audio/": "audio", "/video/": "video"}
LINKED_PREFIXES = ("docs:", "images:", "audio:", "video:")

COPY_NOTE = ("This is a copy for reading: changes to it go nowhere. It "
             "has no codings, and it is the document as it was imported, "
             "so it is not pseudonymised.")


# Only an original of a type QualCoder imports is copied and shown (a web
# page original is only shown, never opened: opener.openable). Anything
# else in a project, such as a program or a shortcut from someone else's
# project, could act when double-clicked, read-only or not, so Exegete
# neither copies nor shows it.
NOT_A_DOCUMENT_TYPE = (
    "This original is not one of the document or media types QualCoder "
    "imports, so Exegete neither copies nor shows it: a file of another "
    "type, such as a program or a shortcut, could act when opened. Ask "
    "whoever made the project what the file is.")


def copied_type(name: str) -> bool:
    """Whether an original with this name is of a type Exegete copies
    and shows: the document and media types QualCoder imports, and web
    pages (shown only)."""
    suffix = os.path.splitext(name)[1].lower()
    return suffix in opener.OPENABLE or suffix in opener.WEB_PAGES


class ReadingRefusal(Exception):
    """A plain refusal, for the answer."""


def page_name(file_name: str) -> str:
    return f"{reading_folder.safe_name(file_name)} - reading copy.html"


def original_source(project: Path, mediapath: Optional[str]
                    ) -> Tuple[Optional[Path], Optional[str]]:
    """(the project's stored original, None) or (None, why there is none
    to open): no stored path, a linked one, or one that fails the
    checks. The reason is in plain words, for the answer."""
    if not mediapath:
        return None, "no_original"
    if mediapath.startswith(LINKED_PREFIXES):
        return None, ("This file's original is linked from elsewhere on "
                      "the computer, not kept in the project, so Exegete "
                      "does not open it; QualCoder's Manage files opens "
                      "it.")
    for prefix, folder_name in STORED_FOLDERS.items():
        if mediapath.startswith(prefix):
            name = mediapath[len(prefix):]
            break
    else:
        return None, "The project records no usable place for the original."
    if file_name_problem(name) is not None:
        return None, ("The original's stored name is not one Exegete can "
                      "use safely, so it was not opened; QualCoder's "
                      "Manage files opens it.")
    if not copied_type(name):
        return None, NOT_A_DOCUMENT_TYPE
    folder = project / folder_name
    try:
        folder_info = os.lstat(folder)
    except OSError:
        folder_info = None
    if folder_info is None or not stat.S_ISDIR(folder_info.st_mode) or \
            reading_folder.is_link(folder) or not is_inside(folder, project):
        return None, ("The project's own folder of originals "
                      f"('{folder_name}') is missing or is not an ordinary "
                      "folder, so Exegete does not open anything from it.")
    source = folder / name
    try:
        info = os.lstat(source)
    except OSError:
        return None, ("The original is missing from the project's own "
                      f"folder of originals ('{folder_name}').")
    if not stat.S_ISREG(info.st_mode) or not is_inside(source, folder):
        return None, ("The original in the project is not an ordinary "
                      "file, so Exegete does not open it.")
    return source, None


def write_reading_copy(project: Path, file_id: int, **page) -> Tuple[
        Path, Dict[str, Any]]:
    """Build and write a file's reading copy; (its place, its counts)."""
    html, counts = reading_copy.build_page(file_id=file_id, **page)
    folder = reading_folder.file_folder(project, file_id)
    path = reading_folder.write_page(folder, page_name(page["file_name"]),
                                     html)
    return path, counts


def copy_original(project: Path, file_id: int, source: Path) -> Path:
    """A read-only copy of the original in the file's reading folder,
    under a name that ends as the original's does: the type rule holds
    for the copy's own name too, so a long name cut to fit never makes a
    document's copy a program's."""
    name = reading_folder.safe_file_name(source.name, 120)
    if not copied_type(name) or (os.path.splitext(name)[1].lower()
                                 != os.path.splitext(source.name)[1].lower()):
        raise ReadingRefusal(NOT_A_DOCUMENT_TYPE)
    folder = reading_folder.original_folder(project, file_id)
    return reading_folder.copy_read_only(source, folder, name)


def present(path: Path, how: str, own_page: bool) -> Dict[str, Any]:
    """Open or show a file Exegete has just written, and say what
    happened. `how` is 'open' or 'show'."""
    top = reading_folder.root()
    if not is_inside(path, top):
        raise ReadingRefusal("Exegete opens only files in its own reading "
                             "folder.")
    if how == "open":
        outcome = opener.open_file(path, own_page=own_page)
    else:
        outcome = opener.show_in_folder(path)
    result: Dict[str, Any] = {
        "opened" if how == "open" else "shown_in_folder": outcome.done}
    if not outcome.done:
        result["not_opened_because"] = outcome.reason
    return result


def now() -> datetime:
    return datetime.now()
