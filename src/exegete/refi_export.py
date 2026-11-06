# SPDX-License-Identifier: LGPL-3.0-or-later
"""REFI-QDA XML export: a whole project, or one AI coding session.

Generates REFI-QDA compliant XML files (.qdpx) that can be imported into
Qualcoder and other QDA software supporting the REFI-QDA standard
(QDA-XML 1.0, specification document v1.5).

Position convention (QualCoder's, shared by this database): character
offsets into the plain text as stored, 0-based, end-exclusive, newlines
are single \n characters. The exported .txt payloads are written verbatim
(UTF-8, no BOM) so positions remain valid on re-import.

A whole-project export (v0.15.3, ruling 85, item 2; ruling 115, item 1)
writes each coding under its own coder, the whole codebook, every text
source, the cases with their attributes and whole-file links, the journal
entries and the annotations. What the file cannot hold faithfully is left
out and counted: images, audio, video and PDF page areas; a case's link
to part of a file; a numeric attribute's value that is not a number; an
annotation whose positions do not fit its text. Every text and journal
entry is read once, before anything is written, and the archive is
written beside its destination and moved into place only when complete.
"""

import os
import re
import stat
import time
import uuid
import logging
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from decimal import Decimal
from xml.dom import minidom
import zipfile
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone

from . import names
from .database import (DatabaseLockedError, QualcoderDatabase,
                       _raise_query_error, error_label, error_text,
                       finite_number)
from .new_project import WINDOWS_MAX_FILE_PATH
from .sessions import CodingSuggestion, memo_with_reading

logger = logging.getLogger(__name__)

# REFI-QDA XML namespace: "1.5" is the revision of the SPEC DOCUMENT; the
# wire format is QDA-XML 1.0 and this is its one and only namespace.
NAMESPACE = "urn:QDA-XML:project:1.0"
SCHEMA_LOCATION = (
    "urn:QDA-XML:project:1.0 "
    "http://schema.qdasoftware.org/versions/Project/v1.0/Project.xsd"
)

# GUIDType pattern from the spec (optionally brace-wrapped is also legal,
# but we always emit the bare lowercase form)
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# RGBType pattern from the spec
_COLOR_RE = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")

# Spec §8.5: max internal file size
_MAX_INTERNAL_FILE_BYTES = 2_147_483_647

# A session suggestion's status, in the words its Description starts with
# (sessions.py, CodingSuggestion.status); any other value is "unknown"
SUGGESTION_STATUSES = ("pending", "approved", "rejected", "applied",
                       "removed")

# The refusal of a project the file could carry nothing of (v0.15.3: a
# project without codings exports, as long as it holds any of these)
EMPTY_PROJECT_REFUSAL = (
    "The project has no codes, categories, text sources, cases or journal "
    "entries to export.")

# The part file: the archive is written beside its destination under
# this name and moved into place only when complete. The destination's
# name is cut to its first PART_NAME_BYTES bytes in UTF-8, so the part's
# name stays within the 255 bytes a file name may hold.
PART_NAME_BYTES = 100
_PART_RE = re.compile(r"\.(.*)\.([0-9]+)-([0-9]+)\.part",
                      re.IGNORECASE | re.DOTALL)
_PART_FLAGS = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
               | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))

# A stored date in QualCoder's form, "YYYY-MM-DD HH:MM:SS" (local time),
# or a date alone
_STORED_DATE_RE = re.compile(
    r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:[ T]([0-9]{2}:[0-9]{2}:[0-9]{2}))?")


def _xml_safe(text) -> str:
    """Strip characters that are invalid in XML 1.0 from a string.

    ElementTree will happily serialise C0 control characters, but the
    result is not well-formed XML: minidom (and any conformant parser,
    including the QDA tools importing the .qdpx) rejects it. Database
    content (code names, memos, file names) is user-authored and may
    contain such characters, so every DB-derived string is filtered
    before it enters the XML tree.

    Valid XML 1.0 chars: #x9 #xA #xD, #x20-#xD7FF, #xE000-#xFFFD,
    #x10000-#x10FFFF (surrogates excluded by the D7FF/E000 bounds).
    """
    if text is None:
        return ""
    return "".join(
        ch for ch in str(text)
        if ch in ("\t", "\n", "\r")
        or 0x20 <= ord(ch) <= 0xD7FF
        or 0xE000 <= ord(ch) <= 0xFFFD
        or 0x10000 <= ord(ch) <= 0x10FFFF
    )


def _utc_now() -> str:
    """xsd:dateTime in actual UTC (not local time mislabelled as Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _note_datetime(stored: Any) -> str:
    """A row's stored date as xsd:dateTime, for a Note's two dates.

    QualCoder stores local time as "YYYY-MM-DD HH:MM:SS"; it is written
    with a T and no zone, since local time carries none (QualCoder's own
    export adds a Z, which would call it UTC). A date alone is written at
    midnight. Any other value, or none, gives the export's own time:
    QualCoder 4.0's importer fails on a Note with neither date.
    """
    if isinstance(stored, str):
        match = _STORED_DATE_RE.fullmatch(stored.strip())
        if match is not None:
            text = f"{match.group(1)}T{match.group(2) or '00:00:00'}"
            try:
                datetime.strptime(text, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
            else:
                return text
    return _utc_now()


def plain_decimal(number: float) -> str:
    """A finite number in xsd:decimal's plain notation, in its shortest
    form: no exponent ("1e3" is 1000), no trailing zeros ("40.50" is
    40.5). Written from the float `finite_number` returns, so it takes at
    most 326 characters (for 5e-324), where the stored text's own decimal
    form has no bound."""
    return format(Decimal(repr(number)).normalize(), "f")


def export_read_refusal(kind: str) -> str:
    """The answer when a read of the project fails during an export: the
    kind of row, never its text (SQLite's message can quote a value)."""
    return (f"The export stopped before writing anything: Exegete could not "
            f"read the project's {kind}. A row that another program stored "
            f"in an encoding other than UTF-8 is one cause. An earlier file "
            f"of that name is unchanged.")


def read_for_export(kind: str, read: Callable[[], Any]) -> Any:
    """`read()`, with any failure of the database worded by the kind of
    row being read: a busy database keeps its own text
    (`_raise_query_error`), and any other SQLite error stops the export
    in words naming `kind` and never the row's text. Reads that word
    SQLite's error themselves (`get_file_content` and the others) are
    worded again the same way."""
    try:
        return read()
    except DatabaseLockedError:
        raise
    except sqlite3.Error as e:
        _raise_query_error(e, "export_refi_qda", export_read_refusal(kind))
    except RuntimeError:
        raise RuntimeError(export_read_refusal(kind)) from None


def cut_name(name: str, limit: int = PART_NAME_BYTES) -> str:
    """`name` cut to its first `limit` bytes in UTF-8, at a character's
    end."""
    data = name.encode("utf-8", "surrogatepass")
    if len(data) <= limit:
        return name
    return data[:limit].decode("utf-8", "ignore")


def part_name(destination_name: str, pid: int, ns: int) -> str:
    """The part file's name: a dot (so Finder does not show one left
    behind), the destination's name cut, the process id and the time in
    nanoseconds, and `.part`."""
    return f".{cut_name(destination_name)}.{pid}-{ns}.part"


def _part_key(name: str) -> str:
    """How two part files' names are compared: without regard to letter
    case or to Unicode's two ways of writing an accented letter."""
    return unicodedata.normalize("NFC", name).casefold()


def part_path_refusal(destination: Path, on_windows: bool,
                      long_paths: bool) -> Optional[str]:
    """The refusal of an export whose part file, or destination, Windows
    could not open, or None. As `new_project.windows_path_refusal` refuses
    a project: on Windows with long paths off (it leaves them off by
    default), a file cannot be opened at more than WINDOWS_MAX_FILE_PATH
    characters. Called before anything is read or written."""
    if not on_windows or long_paths:
        return None
    part = destination.parent / part_name(destination.name, os.getpid(),
                                          time.time_ns())
    if len(str(destination)) > WINDOWS_MAX_FILE_PATH:
        why = f"the export's path is {len(str(destination))} characters"
    elif len(str(part)) > WINDOWS_MAX_FILE_PATH:
        why = (f"Exegete writes the file beside its destination under a "
               f"longer name first, which needs a path of "
               f"{len(str(part))} characters")
    else:
        return None
    return (f"The export's path would be too long for Windows: {why}, and "
            f"Windows cannot open a file beyond {WINDOWS_MAX_FILE_PATH} "
            f"characters unless long paths are switched on. Choose a "
            f"shorter name, or a folder nearer the top of the disk.")


class ExportWriteError(RuntimeError):
    """The archive could not be written or put in place. Its message says
    what is left: the earlier file unchanged, and a part file only when
    its removal was refused too, by name."""


class _FileAppeared(Exception):
    """With `overwrite` false, a file took the destination's name while
    the export was written."""


def remove_earlier_parts(folder: Path, destination_name: str,
                         before_ns: int) -> int:
    """Remove Exegete's part files of this destination made before
    `before_ns` (an export killed before its replace leaves one), and
    count them.

    Only a regular file (by `lstat`) named exactly a dot, the cut name, a
    dot, digits, a hyphen, digits and `.part`, compared without regard to
    letter case and never through a glob (a name may hold `[`, `*` or
    `?`). One that cannot be removed (on Windows, one still open) is
    skipped and not counted; nothing here fails the export."""
    key = _part_key(cut_name(destination_name))
    try:
        with os.scandir(folder) as listing:
            entries = [(entry.name, entry.path) for entry in listing]
    except OSError as e:
        logger.warning("Earlier part files could not be listed: %s",
                       error_label(e))
        return 0
    removed = 0
    for name, path in entries:
        match = _PART_RE.fullmatch(name)
        if match is None or _part_key(match.group(1)) != key:
            continue
        if int(match.group(3)) >= before_ns:
            continue
        try:
            if not stat.S_ISREG(os.lstat(path).st_mode):
                continue
            os.remove(path)
        except OSError as e:
            logger.warning("An earlier part file could not be removed: %s",
                           error_label(e))
            continue
        removed += 1
    if removed:
        logger.info("Removed %s earlier part file(s) of an export", removed)
    return removed


def _earlier_mode(destination: Path) -> Optional[int]:
    """The earlier file's permission bits, masked to 0o666, or None when
    there is no earlier file."""
    try:
        return stat.S_IMODE(os.stat(destination).st_mode) & 0o666
    except FileNotFoundError:
        return None


def _identity(path: Path) -> Any:
    """What tells one file under `path` from another: its device, inode,
    size and time of change; None when there is no file, and "unknown"
    when it cannot be read."""
    try:
        state = os.stat(path)
    except FileNotFoundError:
        return None
    except OSError:
        return "unknown"
    return (state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns)


def _after_a_failure(destination: Path, before: Any) -> str:
    """What a failed export's answer says of the file under its name:
    unchanged only when it is still the file that was there before the
    export began. Another export to that name that finishes first
    replaces it, and removes this export's part file."""
    now = _identity(destination)
    if "unknown" in (before, now) or (before is None and now is None):
        return "Nothing was written under that name."
    if now == before:
        return "The earlier file of that name is unchanged."
    return ("The file of that name was changed meanwhile, by another "
            "export to that name or by another program.")


def write_beside_and_replace(destination: Path,
                             fill: Callable[[BinaryIO], None],
                             overwrite: bool) -> int:
    """Write the file beside `destination`, then move it into place in one
    `os.replace`; return how many earlier part files were removed.

    The part file is made with `O_EXCL` and, without following a link,
    with the earlier file's permission bits masked to 0o666 (else 0o666),
    which the umask can only narrow, so no text is ever more widely
    readable while written than the earlier file kept it. It is written,
    flushed, synced and closed (Windows renames no open file), given
    those bits again where the file system allows it (nothing on
    Windows, where chmod moves only the read-only flag), and replaced
    onto the destination. The destination is never removed, emptied or
    opened before the replace. With `overwrite` false, the destination
    is checked again just before it.

    Raises:
        ValueError: with `overwrite` false, a file took the name meanwhile
        ExportWriteError: any other failure, the part file removed, or
            named when its removal was refused too
    """
    folder = destination.parent
    part: Optional[Path] = None
    made = False
    before: Any = "unknown"
    try:
        before = _identity(destination)
        earlier = _earlier_mode(destination)
        own_ns = time.time_ns()
        part = folder / part_name(destination.name, os.getpid(), own_ns)
        descriptor = os.open(part, _PART_FLAGS,
                             0o666 if earlier is None else earlier)
        made = True
        try:
            handle = os.fdopen(descriptor, "wb")
        except BaseException:
            os.close(descriptor)
            raise
        with handle:
            fill(handle)
            handle.flush()
            os.fsync(handle.fileno())
        if earlier is not None and os.name != "nt":
            try:
                os.chmod(part, earlier)
            except OSError as refused:
                # As _inherit_mode_bits: the part file was made with these
                # bits, which the umask can only have narrowed
                logger.warning("The export's permission bits could not be "
                               "set: %s", error_label(refused))
        if not overwrite and os.path.lexists(destination):
            raise _FileAppeared()
        os.replace(part, destination)
        made = False
    except BaseException as e:
        left = None
        if made:
            try:
                os.remove(part)
            except FileNotFoundError:
                # Removed meanwhile, as another export to that name
                # removes the part files made before its own
                pass
            except OSError as removal:
                logger.error("The unfinished export could not be removed: "
                             "%s", error_label(removal))
                left = part.name
        if not isinstance(e, Exception):
            raise
        kept = (f" Exegete could not remove the unfinished file it was "
                f"writing beside it, '{left}': it holds the export's texts "
                f"and memos, and can be deleted." if left else "")
        if isinstance(e, _FileAppeared):
            raise ValueError(
                f"'{destination.name}' already exists. Pass overwrite=true "
                f"to replace it.{kept}") from None
        logger.error("The REFI-QDA archive could not be written or put in "
                     "place: %s", error_label(e))
        raise ExportWriteError(
            f"REFI-QDA export failed: {error_text(e)}. "
            f"{_after_a_failure(destination, before)}{kept}") from None
    return remove_earlier_parts(folder, destination.name, own_ns)


def _status_word(status: Any) -> str:
    """A suggestion's status in words, "unknown" for any other value."""
    return status if status in SUGGESTION_STATUSES else "unknown"


def _whole_file_link(pos0: Any, pos1: Any, length: int) -> bool:
    """Whether a case's link covers the whole file: both positions 0, as
    QualCoder writes for a file as a whole, or a span from the start to
    the text's end or one short, the two conventions QualCoder's windows
    store, or past it (`link_file_to_case` treats each as the same
    whole-file link)."""
    if (not isinstance(pos0, int) or isinstance(pos0, bool)
            or not isinstance(pos1, int) or isinstance(pos1, bool)):
        return False
    if pos0 == 0 and pos1 == 0:
        return True
    return pos0 <= 0 and pos1 >= length - 1


def _fitting_positions(pos0: Any, pos1: Any, length: int) -> bool:
    """The positions a coding needs: whole numbers, the start from 0 and
    before the end, the end within the text's length."""
    if (not isinstance(pos0, int) or isinstance(pos0, bool)
            or not isinstance(pos1, int) or isinstance(pos1, bool)):
        return False
    return 0 <= pos0 < pos1 <= length


class _Users:
    """The file's users (v0.15.3): one per name that owns something the
    file holds, keyed by the name as written, the AI coder's under its
    stable "ai_coder" GUID, so no two share a name or a GUID."""

    def __init__(self, db: QualcoderDatabase, ai_user_name: str,
                 used_guids: Set[str]):
        self.db = db
        self.ai_name = _xml_safe(ai_user_name)
        self.ai_guid = db.get_or_create_user_guid("ai_coder")
        self.used = used_guids
        self.used.add(self.ai_guid)
        self.guids: Dict[str, str] = {}
        self.owners: Set[str] = set()

    def guid(self, name: Any, owns: bool = True) -> Optional[str]:
        """The GUID of the User a row's owner is, or None for a row with
        no owner, which is then written without a creatingUser (QualCoder
        writes an empty one, which the schema's GUIDType refuses). The
        AI coder's name (the project's AI coder name, the name its
        codings carry) is the "ai_coder" User."""
        key = _xml_safe(name)
        if key == "":
            return None
        if key == self.ai_name:
            return self.ai_guid
        if key not in self.guids:
            # From "coder" and the name: never the AI's, even for a
            # coder named "ai_coder"
            guid = self.db.generate_deterministic_guid("coder", key)
            if guid in self.used:
                guid = str(uuid.uuid4())
            self.used.add(guid)
            self.guids[key] = guid
        if owns:
            self.owners.add(key)
        return self.guids[key]

    def write(self, users_elem: ET.Element, coder_name: Any) -> None:
        """The project's coder name first, when set and not the AI's,
        whether or not it owns a row (QualCoder's importer makes the
        first User its coder name); then the other owners by name; the
        AI's last, so that it comes first only where no one else is
        named."""
        first = _xml_safe(coder_name)
        order: List[str] = []
        if first and first != self.ai_name:
            self.guid(first, owns=False)
            order.append(first)
        order += sorted(self.owners - set(order))
        for key in order:
            ET.SubElement(users_elem, f"{{{NAMESPACE}}}User",
                          attrib={"guid": self.guids[key], "name": key})
        ET.SubElement(users_elem, f"{{{NAMESPACE}}}User",
                      attrib={"guid": self.ai_guid, "name": self.ai_name})


class RefiQdaExporter:
    """Generate REFI-QDA files from coding suggestions or a whole
    project."""

    def __init__(self, db: QualcoderDatabase,
                 ai_user_name: str = "AI Coding Assistant"):
        """Initialise exporter with database connection.

        Args:
            db: QualcoderDatabase instance
            ai_user_name: Display name for the AI coder User element
                (P1-2: the server passes the configured coder name).
                The deterministic GUID key stays "ai_coder" so the
                same project always exports the same User guid.
        """
        self.db = db
        self.ai_user_name = ai_user_name
        # What the last file built holds and leaves out, by count
        self.counts: Dict[str, Any] = {}

    def create_project_xml(
        self,
        suggestions: List[CodingSuggestion],
        project_name: str = "AI Coding Suggestions",
        origin: str = names.SERVER_NAME,
        owners: Optional[Dict[str, Any]] = None,
        coder_name: Optional[str] = None,
        whole_project: bool = False,
        mark_status: bool = False,
        texts: Optional[Dict[int, Optional[Dict[str, Any]]]] = None,
    ) -> ET.Element:
        """Create the main REFI-QDA project XML structure.

        Args:
            suggestions: List of coding suggestions to export
            project_name: Name for the REFI-QDA project
            origin: Software origin identifier
            owners: Each suggestion's owner, by its guid (a suggestion
                not named here is the AI coder's; None names no owner)
            coder_name: The project's coder name, the first User when set
                and not the AI's
            whole_project: Write the whole project (the whole codebook,
                every text source, cases, attributes and notes); with it
                false, the suggestions' codes and text sources alone
            mark_status: Start each selection's Description with its
                suggestion's status (a session export)
            texts: Texts already read, by file id (each read once)

        Returns:
            XML Element representing the project
        """
        root, _members = self._build(
            suggestions, project_name, origin, owners, coder_name,
            whole_project, mark_status, dict(texts or {}))
        return root

    def _text(self, file_id: int,
              texts: Dict[int, Optional[Dict[str, Any]]]
              ) -> Optional[Dict[str, Any]]:
        """A text source's content, read once and kept in `texts`."""
        if file_id not in texts:
            texts[file_id] = read_for_export(
                "text sources", lambda: self.db.get_file_content(file_id))
        return texts[file_id]

    def _build(self, suggestions, project_name, origin, owners, coder_name,
               whole_project, mark_status, texts
               ) -> Tuple[ET.Element, List[Tuple[str, str]]]:
        """The document and its members (path, text), from one read of
        each text and journal entry: every read is made here, before the
        caller writes anything."""
        # Register namespace
        ET.register_namespace('', NAMESPACE)

        used_guids: Set[str] = set()
        users = _Users(self.db, self.ai_user_name, used_guids)
        self.counts = {}

        # Create root element. NOTE: attributes are UNQUALIFIED in the
        # REFI-QDA schema (attributeFormDefault="unqualified") — a
        # namespaced name attribute would be schema-invalid.
        root = ET.Element(
            f"{{{NAMESPACE}}}Project",
            attrib={
                "name": _xml_safe(project_name),
                "origin": _xml_safe(origin),
                "creatingUserGUID": users.ai_guid,
                "creationDateTime": _utc_now()
            }
        )

        # Add schema location
        root.set(
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
            SCHEMA_LOCATION
        )

        # The XSD sequence: Users, CodeBook, Variables, Cases, Sources,
        # Notes, each written only when it has a child. Users is filled
        # last, once every owner of what is written is known.
        users_elem = ET.SubElement(root, f"{{{NAMESPACE}}}Users")
        codes_written = self._add_codebook_section(
            root, suggestions, whole_project, used_guids)

        file_guids = read_for_export("text sources", self.db.get_file_guids)
        used_guids.update(file_guids.values())
        if whole_project:
            for file_id in sorted(file_guids):
                self._text(file_id, texts)
            written = [fid for fid in sorted(file_guids)
                       if (texts.get(fid) or {}).get("is_text")
                       and (texts.get(fid) or {}).get("content")]
        else:
            written = []
            for suggestion in suggestions:
                fid = suggestion.file_id
                if fid in written or fid not in file_guids:
                    continue
                if (self._text(fid, texts) or {}).get("content"):
                    written.append(fid)
                else:
                    # Never emit a TextSource whose payload will not be
                    # written: a dangling plainTextPath crashes
                    # QualCoder's importer. export_to_qdpx validates this
                    # up front, so this is only a defensive skip for
                    # direct callers.
                    logger.warning("Skipping a file with no text content "
                                   "to export")

        members: List[Tuple[str, str]] = []
        values: Dict[Tuple[str, Any], List[Dict[str, Any]]] = {}
        annotations: Dict[int, List[Dict[str, Any]]] = {}
        journals: List[Dict[str, Any]] = []
        cases_written = 0
        if whole_project:
            variables, values, value_rows = self._read_attributes(used_guids)
            self._add_variables_section(root, variables)
            journals = sorted(
                read_for_export("journal entries",
                                self.db.get_journal_entries),
                key=lambda entry: (entry["id"] is None, entry["id"]))
            annotations = self._annotations_to_write(written, texts,
                                                     used_guids)
            cases = read_for_export("cases", self.db.list_cases)
            cases_written = self._add_cases_section(
                root, cases, variables, values, written, texts, file_guids,
                used_guids)
            self._count_values_left_out(
                value_rows, variables, written, cases, journals, file_guids)
        else:
            variables = {}

        self._add_sources_section(
            root, suggestions, written, texts, file_guids,
            codes_written["guids"], users, owners, whole_project,
            mark_status, annotations, variables, values, used_guids)
        for fid in written:
            members.append((f"sources/{file_guids[fid]}.txt",
                            texts[fid]["content"]))

        if whole_project:
            members += self._add_notes_section(
                root, journals, annotations, users, used_guids)
            if not (codes_written["elements"] or written or cases_written
                    or journals):
                raise ValueError(EMPTY_PROJECT_REFUSAL)

        users.write(users_elem, coder_name)

        self.counts.update({
            "codes": codes_written["codes"],
            "text_sources": len(written),
        })
        if whole_project:
            self.counts.update({
                "cases": cases_written,
                "journal_entries": len(journals),
                "annotations": sum(len(rows)
                                   for rows in annotations.values()),
            })
        if mark_status:
            by_status = {word: 0 for word in SUGGESTION_STATUSES}
            for suggestion in suggestions:
                word = _status_word(suggestion.status)
                by_status[word] = by_status.get(word, 0) + 1
            self.counts["suggestions_by_status"] = by_status
        return root, members

    def _add_codebook_section(
        self,
        root: ET.Element,
        suggestions: List[CodingSuggestion],
        whole_project: bool = False,
        used_guids: Optional[Set[str]] = None,
    ) -> Dict[str, int]:
        """Add CodeBook section with codes referenced in suggestions, or
        with every code and category (`whole_project`, as QualCoder's own
        export writes the codebook, v0.15.3). Written only when it has a
        code or a category; returns how many elements, and how many
        codable codes, it wrote, and the codes' GUIDs, read once.

        Category hierarchy is preserved: REFI-QDA expresses categories as
        nested Code elements with isCodable="false" (QualCoder's own
        convention on both export and import), so referenced codes are
        emitted inside their full category chain.

        Sub-codes (S9, v16+): a referenced sub-code is emitted NESTED
        inside its parent code's codable Code element, recursively, with
        the whole parent-code chain included, matching master's export
        (refi.py:3228-3248; top-level condition :3279-3281). Master's
        importer reconstructs supercid from codable children of codable
        codes (refi.py:242-254), so a correct export round-trips instead
        of silently flattening the hierarchy. A loop in the tree of
        categories or of codes (a damaged project) is cut where it would
        close, that element going to the top.

        Args:
            root: Root XML element
            suggestions: List of coding suggestions
            whole_project: Every code and category, referenced or not
            used_guids: GUIDs already in the document, added to
        """
        used_guids = used_guids if used_guids is not None else set()
        code_guids = read_for_export("codes and categories",
                                     self.db.get_code_guids)
        all_codes = {c["id"]: c for c in read_for_export(
            "codes and categories", self.db.list_codes)}
        all_categories = {c["id"]: c for c in read_for_export(
            "codes and categories", self.db.list_categories)}

        if whole_project:
            needed_codes: Set[int] = set(all_codes)
            needed_categories: Set[int] = set(all_categories)
        else:
            code_ids = set(s.code_id for s in suggestions)
            # Sub-codes: pull each referenced code's parent-code chain
            # into the export too (the sub-code must nest inside its
            # parent element)
            needed_codes = set()
            for code_id in code_ids:
                current = code_id
                seen_codes: Set[int] = set()
                while current in all_codes and current not in seen_codes:
                    seen_codes.add(current)
                    needed_codes.add(current)
                    parent = all_codes[current].get("parent_code_id")
                    if parent is None:
                        break
                    current = parent

            # Which categories are needed? Walk each needed code's chain up
            needed_categories = set()
            for code_id in needed_codes:
                code = all_codes.get(code_id)
                if not code:
                    continue
                cat_id = code.get("category_id")
                seen: Set[int] = set()
                while (cat_id is not None and cat_id in all_categories
                       and cat_id not in seen):
                    seen.add(cat_id)
                    needed_categories.add(cat_id)
                    cat_id = all_categories[cat_id].get("parent_id")

        if not needed_codes and not needed_categories:
            return {"elements": 0, "codes": 0, "guids": code_guids}
        codebook_elem = ET.SubElement(root, f"{{{NAMESPACE}}}CodeBook")
        codes_elem = ET.SubElement(codebook_elem, f"{{{NAMESPACE}}}Codes")

        category_elems: Dict[int, ET.Element] = {}

        def _category_elem(cat_id: int, trail: Tuple[int, ...] = ()
                           ) -> ET.Element:
            """Get or create the (nested) element for a category."""
            if cat_id in category_elems:
                return category_elems[cat_id]
            cat = all_categories[cat_id]
            parent_id = cat.get("parent_id")
            if (parent_id is not None and parent_id in needed_categories
                    and parent_id != cat_id and parent_id not in trail):
                parent_elem = _category_elem(parent_id, trail + (cat_id,))
            else:
                parent_elem = codes_elem
            guid = self.db.generate_deterministic_guid("category", cat_id)
            used_guids.add(guid)
            elem = ET.SubElement(
                parent_elem,
                f"{{{NAMESPACE}}}Code",
                attrib={
                    "guid": guid,
                    "name": _xml_safe(cat["name"]),
                    "isCodable": "false"
                }
            )
            if cat.get("memo"):
                desc = ET.SubElement(elem, f"{{{NAMESPACE}}}Description")
                desc.text = _xml_safe(cat["memo"])
            category_elems[cat_id] = elem
            return elem

        # Emit categories root-down (recursion in _category_elem builds
        # parents first)
        for cat_id in sorted(needed_categories):
            _category_elem(cat_id)

        # Emit the needed codes: a top-level code goes inside its category
        # chain (or Codes root); a sub-code nests inside its parent code's
        # element, recursively (S9)
        code_elems: Dict[int, ET.Element] = {}

        def _code_elem(code_id: int, trail: Tuple[int, ...] = ()):
            if code_id in code_elems:
                return code_elems[code_id]
            code = all_codes.get(code_id)
            if not code:
                logger.warning("Could not export a code: not found")
                return None
            parent_code = code.get("parent_code_id")
            if (parent_code is not None and parent_code in needed_codes
                    and parent_code != code_id and parent_code not in trail):
                parent_elem = _code_elem(parent_code, trail + (code_id,))
                if parent_elem is None:
                    parent_elem = codes_elem
            else:
                cat_id = code.get("category_id")
                parent_elem = (category_elems.get(cat_id, codes_elem)
                               if cat_id is not None else codes_elem)

            used_guids.add(code_guids[code_id])
            elem = ET.SubElement(
                parent_elem,
                f"{{{NAMESPACE}}}Code",
                attrib={
                    "guid": code_guids[code_id],
                    "name": _xml_safe(code["name"]),
                    "isCodable": "true"
                }
            )
            # Add color only when it is a valid RGBType value
            color = code.get("color")
            if color and _COLOR_RE.match(str(color)):
                elem.set("color", str(color))
            # Add description (memo) only when non-empty
            if code.get("memo"):
                desc_elem = ET.SubElement(elem, f"{{{NAMESPACE}}}Description")
                desc_elem.text = _xml_safe(code["memo"])
            code_elems[code_id] = elem
            return elem

        for code_id in sorted(needed_codes):
            _code_elem(code_id)
        return {"elements": len(category_elems) + len(code_elems),
                "codes": len(code_elems), "guids": code_guids}

    def _read_attributes(self, used_guids: Set[str]):
        """The case and file attribute types as Variables (numeric as
        Float, else Text; a journal's left out), by kind and name, and
        every attribute value, by what it is set on."""
        types = read_for_export("attributes", self.db.list_attribute_types)
        variables: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for attribute in types:
            kind = attribute.get("applies_to")
            if kind not in ("case", "file"):
                continue
            # From the attribute type's name, the table's key
            guid = self.db.generate_deterministic_guid(
                "variable", attribute["name"])
            if guid in used_guids:
                guid = str(uuid.uuid4())
            used_guids.add(guid)
            variables[(kind, attribute["name"])] = {
                "guid": guid, "name": attribute["name"],
                "numeric": attribute.get("value_type") == "numeric",
                "memo": attribute.get("memo") or "",
            }
        known = {(t.get("applies_to"), t["name"]) for t in types}
        rows = [row for row in read_for_export(
                    "attributes", self.db.list_attribute_values)
                if (row["attr_type"], row["name"]) in known
                and not _unset(row["value"])]
        values: Dict[Tuple[str, Any], List] = {}
        for row in rows:
            values.setdefault((row["attr_type"], row["id"]), []).append(row)
        return variables, values, rows

    def _add_variables_section(self, root: ET.Element,
                               variables: Dict[Tuple[str, str],
                                               Dict[str, Any]]) -> None:
        """Add a Variables section, one Variable per case or file
        attribute type, when there is one."""
        if not variables:
            return
        variables_elem = ET.SubElement(root, f"{{{NAMESPACE}}}Variables")
        for variable in variables.values():
            elem = ET.SubElement(
                variables_elem, f"{{{NAMESPACE}}}Variable",
                attrib={"guid": variable["guid"],
                        "name": _xml_safe(variable["name"]),
                        "typeOfVariable": ("Float" if variable["numeric"]
                                           else "Text")})
            if variable["memo"]:
                desc = ET.SubElement(elem, f"{{{NAMESPACE}}}Description")
                desc.text = _xml_safe(variable["memo"])

    def _add_variable_values(self, parent: ET.Element, kind: str,
                             owner_id: Any, variables, values) -> None:
        """Add a VariableValue for each value set on this case or file.
        A numeric attribute's value is written as FloatValue only when
        `finite_number` reads it as a number, in plain decimal notation;
        any other is left out (counted by `_count_values_left_out`)."""
        for row in values.get((kind, owner_id), []):
            variable = variables.get((kind, row["name"]))
            if variable is None:
                continue
            written = _value_text(row["value"], variable["numeric"])
            if written is None:
                continue
            value_elem = ET.SubElement(parent,
                                       f"{{{NAMESPACE}}}VariableValue")
            ET.SubElement(value_elem, f"{{{NAMESPACE}}}VariableRef",
                          attrib={"targetGUID": variable["guid"]})
            tag = "FloatValue" if variable["numeric"] else "TextValue"
            ET.SubElement(value_elem, f"{{{NAMESPACE}}}{tag}").text = written

    def _count_values_left_out(self, rows, variables, written, cases,
                               journals, file_guids) -> None:
        """Count the values set on a case, a file or a journal entry of
        the project that the file does not carry: on a file not written,
        on a journal entry, and a numeric attribute's value that is not
        a number."""
        case_ids = {case["id"] for case in cases}
        journal_ids = {entry["id"] for entry in journals}
        written_ids = set(written)
        left_out = 0
        for row in rows:
            kind, owner_id = row["attr_type"], row["id"]
            exists = ((kind == "case" and owner_id in case_ids)
                      or (kind == "file" and owner_id in file_guids)
                      or (kind == "journal" and owner_id in journal_ids))
            if not exists:
                continue
            variable = variables.get((kind, row["name"]))
            if (variable is None
                    or (kind == "file" and owner_id not in written_ids)
                    or _value_text(row["value"],
                                   variable["numeric"]) is None):
                left_out += 1
        self.counts["attribute_values_left_out"] = left_out

    def _add_cases_section(self, root, cases, variables, values, written,
                           texts, file_guids, used_guids) -> int:
        """Add a Cases section: each case with its memo as Description,
        its attribute values, and a SourceRef for each whole-file link to
        a text source written. A link to part of a file is left out, as
        QualCoder 4.0's importer would read an uncoded selection as an
        annotation, and so is a link to a file not written; both are
        counted in case_links_left_out."""
        links = read_for_export("case links", self.db.list_case_links)
        self.counts["case_links_left_out"] = 0
        if not cases:
            return 0
        case_guids = read_for_export("cases", self.db.get_case_guids)
        by_case: Dict[Any, List[Dict[str, Any]]] = {}
        for link in links:
            by_case.setdefault(link["case_id"], []).append(link)
        written_ids = set(written)
        cases_elem = ET.SubElement(root, f"{{{NAMESPACE}}}Cases")
        for case in sorted(cases, key=lambda c: c["id"]):
            guid = (case_guids.get(case["id"])
                    or self.db.generate_deterministic_guid("case",
                                                           case["id"]))
            used_guids.add(guid)
            case_elem = ET.SubElement(
                cases_elem, f"{{{NAMESPACE}}}Case",
                attrib={"guid": guid, "name": _xml_safe(case["name"])})
            if case.get("memo"):
                desc = ET.SubElement(case_elem,
                                     f"{{{NAMESPACE}}}Description")
                desc.text = _xml_safe(case["memo"])
            self._add_variable_values(case_elem, "case", case["id"],
                                      variables, values)
            linked: Set[int] = set()
            for link in by_case.get(case["id"], []):
                fid = link["file_id"]
                if (fid in written_ids and _whole_file_link(
                        link["pos0"], link["pos1"],
                        len(texts[fid]["content"]))):
                    if fid not in linked:
                        linked.add(fid)
                        ET.SubElement(case_elem, f"{{{NAMESPACE}}}SourceRef",
                                      attrib={"targetGUID": file_guids[fid]})
                else:
                    self.counts["case_links_left_out"] += 1
        return len(cases)

    def _annotations_to_write(self, written, texts, used_guids
                              ) -> Dict[int, List[Dict[str, Any]]]:
        """The annotations the file holds, by file: those on a text source
        written, with the positions a coding needs, each given its Note's
        and its selection's GUID. One with a NULL position (the table
        allows it; it would reach startPosition, an xsd:integer, as
        "None", and stop QualCoder's importer at int(pos0)), reaching
        past its text, or on a file not written is left out and counted
        in annotations_left_out."""
        rows = read_for_export("annotations", self.db.list_annotations)
        written_ids = set(written)
        by_file: Dict[int, List[Dict[str, Any]]] = {}
        left_out = 0
        for row in rows:
            fid = row["file_id"]
            if (fid in written_ids and _fitting_positions(
                    row["position_start"], row["position_end"],
                    len(texts[fid]["content"]))):
                anid = row["annotation_id"]
                row["note_guid"] = self._new_guid("annotation", anid,
                                                  used_guids)
                row["selection_guid"] = self._new_guid(
                    "annotation selection", anid, used_guids)
                by_file.setdefault(fid, []).append(row)
            else:
                left_out += 1
        self.counts["annotations_left_out"] = left_out
        return by_file

    def _add_sources_section(
        self,
        root: ET.Element,
        suggestions: List[CodingSuggestion],
        written: List[int],
        texts: Dict[int, Optional[Dict[str, Any]]],
        file_guids: Dict[int, str],
        code_guids: Dict[int, str],
        users: _Users,
        owners: Optional[Dict[str, Any]],
        whole_project: bool,
        mark_status: bool,
        annotations: Dict[int, List[Dict[str, Any]]],
        variables,
        values,
        used_guids: Set[str],
    ) -> None:
        """Add Sources section with files and coded segments.

        Sources are referenced with the internal:// URL scheme and GUID
        filenames per spec §8.3/8.4; QualCoder's importer hard-depends on
        the internal:/ prefix (refi.py:880). In a whole-project export each
        TextSource names its row's owner, and holds a NoteRef for each of
        its annotations written and its file attribute values.
        """
        if not written:
            return
        sources_elem = ET.SubElement(root, f"{{{NAMESPACE}}}Sources")

        # Group suggestions by file
        file_suggestions: Dict[int, List[CodingSuggestion]] = {}
        for suggestion in suggestions:
            file_suggestions.setdefault(suggestion.file_id, []).append(
                suggestion)

        for file_id in written:
            file_content = texts[file_id]
            attrib = {
                "guid": file_guids[file_id],
                "name": _xml_safe(file_content["name"]),
                "plainTextPath": f"internal://{file_guids[file_id]}.txt",
            }
            creator = (users.guid(file_content.get("owner"))
                       if whole_project else users.ai_guid)
            if creator is not None:
                attrib["creatingUser"] = creator
            attrib["creationDateTime"] = _utc_now()
            source_elem = ET.SubElement(
                sources_elem, f"{{{NAMESPACE}}}TextSource", attrib=attrib)

            # Add description (memo) only when non-empty
            if file_content.get("memo"):
                desc_elem = ET.SubElement(source_elem, f"{{{NAMESPACE}}}Description")
                desc_elem.text = _xml_safe(file_content["memo"])

            # Add PlainTextSelection elements for each suggestion
            for suggestion in file_suggestions.get(file_id, []):
                if owners is not None and suggestion.guid in owners:
                    user_guid = users.guid(owners[suggestion.guid])
                else:
                    user_guid = users.ai_guid
                self._add_plain_text_selection(
                    source_elem,
                    suggestion,
                    code_guids,
                    user_guid,
                    used_guids,
                    status=(_status_word(suggestion.status)
                            if mark_status else None),
                )

            # The TextSource sequence: NoteRef before VariableValue. One
            # for every annotation written (QualCoder's export stops at
            # the first, so its importer brings back one per file)
            for row in annotations.get(file_id, []):
                ET.SubElement(source_elem, f"{{{NAMESPACE}}}NoteRef",
                              attrib={"targetGUID": row["note_guid"]})
            if whole_project:
                self._add_variable_values(source_elem, "file", file_id,
                                          variables, values)

    def _add_plain_text_selection(
        self,
        source_elem: ET.Element,
        suggestion: CodingSuggestion,
        code_guids: Dict[int, str],
        user_guid: Optional[str],
        used_guids: Set[str],
        status: Optional[str] = None,
    ) -> None:
        """Create PlainTextSelection element for a coded segment.

        Args:
            source_elem: Parent source element
            suggestion: CodingSuggestion to export
            code_guids: Mapping of code IDs to GUIDs
            user_guid: GUID of the creating user (None: a row with no
                owner, written without one)
            used_guids: GUIDs already used in this document (uniqueness is
                        mandatory within one REFI-QDA document)
            status: The suggestion's status in words, which starts its
                Description (a session export, v0.15.3)
        """
        # Selection GUID: session-supplied values are untrusted — validate
        # the format and document-uniqueness, minting a fresh one otherwise
        selection_guid = suggestion.guid
        if (not isinstance(selection_guid, str)
                or not _GUID_RE.match(selection_guid)
                or selection_guid in used_guids):
            selection_guid = str(uuid.uuid4())
        used_guids.add(selection_guid)

        attrib = {
            "guid": selection_guid,
            "startPosition": str(suggestion.start_pos),
            "endPosition": str(suggestion.end_pos),
        }
        if user_guid is not None:
            attrib["creatingUser"] = user_guid
        attrib["creationDateTime"] = _utc_now()
        selection_elem = ET.SubElement(
            source_elem, f"{{{NAMESPACE}}}PlainTextSelection", attrib=attrib)

        # Description: the status first in a session export, then the
        # reading in words, then the reasoning, as apply_codings writes
        # the memo (owner ruling 21: never a number). First, because a
        # memo holding QualCoder's '#####' private marker keeps only what
        # comes before it. A project export's rows carry no label of their
        # own (reading is None): an applied AI coding's memo already says
        # it in words.
        memo_text = memo_with_reading(suggestion.reasoning or "",
                                      suggestion.reading)
        if status is not None:
            memo_text = "\n\n".join(
                part for part in (f"Status: {status}", memo_text) if part)
        if memo_text:
            desc_elem = ET.SubElement(selection_elem, f"{{{NAMESPACE}}}Description")
            desc_elem.text = _xml_safe(memo_text)

        # Coding GUID: deterministic over file/code/BOTH positions (start
        # alone collided for same-start selections), deduped per document
        coding_guid = self.db.generate_deterministic_guid(
            "coding",
            f"{suggestion.file_id}_{suggestion.code_id}_"
            f"{suggestion.start_pos}_{suggestion.end_pos}"
        )
        if coding_guid in used_guids:
            coding_guid = str(uuid.uuid4())
        used_guids.add(coding_guid)

        coding_attrib = {"guid": coding_guid}
        if user_guid is not None:
            coding_attrib["creatingUser"] = user_guid
        coding_attrib["creationDateTime"] = _utc_now()
        coding_elem = ET.SubElement(
            selection_elem, f"{{{NAMESPACE}}}Coding", attrib=coding_attrib)

        # Add CodeRef pointing to the code
        ET.SubElement(
            coding_elem,
            f"{{{NAMESPACE}}}CodeRef",
            attrib={
                "targetGUID": code_guids[suggestion.code_id]
            }
        )

    def _add_notes_section(self, root, journals, annotations, users,
                           used_guids) -> List[Tuple[str, str]]:
        """Add a Notes section: each journal entry a Note with its name and
        its text as a member, sources/<guid>.txt (UTF-8, no BOM: QualCoder's
        importer opens the member as plain text, and a BOM would come back
        as characters at the entry's start), and each annotation written a
        Note with its memo as PlainTextContent and one PlainTextSelection.
        Every Note has both dates (QualCoder 4.0's importer fails on a
        Note with neither, and takes an annotation's date from
        modifiedDateTime). Returns the journal entries' members."""
        members: List[Tuple[str, str]] = []
        rows = [row for fid in sorted(annotations)
                for row in annotations[fid]]
        if not journals and not rows:
            return members
        notes_elem = ET.SubElement(root, f"{{{NAMESPACE}}}Notes")
        for entry in journals:
            guid = self._new_guid("journal", entry["id"], used_guids)
            when = _note_datetime(entry.get("date"))
            attrib = {"guid": guid, "name": _xml_safe(entry.get("name")),
                      "plainTextPath": f"internal://{guid}.txt"}
            creator = users.guid(entry.get("owner"))
            if creator is not None:
                attrib["creatingUser"] = creator
            attrib["creationDateTime"] = when
            attrib["modifiedDateTime"] = when
            ET.SubElement(notes_elem, f"{{{NAMESPACE}}}Note", attrib=attrib)
            members.append((f"sources/{guid}.txt", entry.get("content") or ""))
        for row in rows:
            when = _note_datetime(row.get("date"))
            attrib = {"guid": row["note_guid"]}
            creator = users.guid(row.get("owner"))
            if creator is not None:
                attrib["creatingUser"] = creator
            attrib["creationDateTime"] = when
            attrib["modifiedDateTime"] = when
            note = ET.SubElement(notes_elem, f"{{{NAMESPACE}}}Note",
                                 attrib=attrib)
            ET.SubElement(note, f"{{{NAMESPACE}}}PlainTextContent").text = \
                _xml_safe(row.get("memo"))
            ET.SubElement(
                note, f"{{{NAMESPACE}}}PlainTextSelection",
                attrib={"guid": row["selection_guid"],
                        "startPosition": str(row["position_start"]),
                        "endPosition": str(row["position_end"])})
        return members

    def _new_guid(self, kind: str, key: Any, used_guids: Set[str]) -> str:
        """A deterministic GUID, checked against the document's as the
        codings' are."""
        guid = self.db.generate_deterministic_guid(kind, key)
        if guid in used_guids:
            guid = str(uuid.uuid4())
        used_guids.add(guid)
        return guid

    def prettify_xml(self, elem: ET.Element) -> str:
        """Convert XML element to pretty-printed string.

        Args:
            elem: XML element to prettify

        Returns:
            Pretty-printed XML string
        """
        # Convert to string
        rough_string = ET.tostring(elem, encoding='utf-8')

        # Parse and prettify. Security note: this parses ONLY the string we
        # just serialized ourselves (never external/untrusted XML), so the
        # stdlib parser's XXE/entity-expansion caveats do not apply here.
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

    def export_to_qdpx(
        self,
        suggestions: List[CodingSuggestion],
        output_path: str,
        project_name: str = "AI Coding Suggestions",
        owners: Optional[Dict[str, Any]] = None,
        coder_name: Optional[str] = None,
        whole_project: bool = False,
        mark_status: bool = False,
        texts: Optional[Dict[int, Optional[Dict[str, Any]]]] = None,
        overwrite: bool = True,
    ) -> str:
        """Export suggestions, or a whole project, as a .qdpx file (ZIP
        with XML).

        Container layout per spec §8: project.qde at the archive root plus
        a flat sources/ folder whose members are GUID-named .txt files
        (UTF-8, no BOM), referenced from the XML as internal://<guid>.txt.

        Suggestions are validated first; stale code/file references,
        out-of-bounds positions, or files without text content fail the
        export loudly instead of producing a .qdpx that crashes importers.
        Every text and journal entry is then read once, and the element
        and the member of each written from that read; every read is made
        before the file is. The archive is written beside the destination
        and moved into place only when complete (`write_beside_and_replace`).

        Args:
            suggestions: List of coding suggestions to export
            output_path: Path where to save the .qdpx file
            project_name: Name for the REFI-QDA project
            owners, coder_name, whole_project, mark_status, texts: as
                `create_project_xml` takes them
            overwrite: Replace a file already at `output_path` (with it
                false, one that appears while the export is written is
                refused)

        Returns:
            Path to created .qdpx file; `counts` then says what the file
            holds and leaves out

        Raises:
            ValueError: If any suggestion fails validation, or the project
                holds nothing the file can carry
            RuntimeError: If a read or the export itself fails
        """
        texts = dict(texts or {})
        # Validate BEFORE building anything (Gap 4: stale IDs used to
        # KeyError mid-export; empty-content files left dangling members).
        # A whole-project export without codings goes ahead.
        if suggestions or not whole_project:
            problems = self.validate_suggestions(suggestions, texts)
            if problems:
                shown = "; ".join(problems[:10])
                more = (f" (+{len(problems) - 10} more)"
                        if len(problems) > 10 else "")
                raise ValueError(f"Export validation failed: {shown}{more}")

        root, members = self._build(
            suggestions, project_name, names.SERVER_NAME, owners,
            coder_name, whole_project, mark_status, texts)

        # Serialize ONCE. The previous minidom pretty-print re-parse
        # roughly doubled peak memory (~147 MB for a 4 MB project) and
        # dominated wall-clock at scale (track6); pretty-printing a
        # machine-interchange file buys nothing. prettify_xml remains
        # available for callers that want readable output.
        xml_string = ET.tostring(root, encoding="unicode",
                                 xml_declaration=True)

        def fill(handle: BinaryIO) -> None:
            with zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # project.qde at the root, lowercase (QualCoder's importer
                # hard-codes this name). Python str -> UTF-8, never a BOM:
                # a BOM would silently shift every position by one on
                # re-import.
                zipf.writestr('project.qde', xml_string)
                # Source payloads and journal entries under
                # sources/<guid>.txt, verbatim (positions are only
                # meaningful against the exact text)
                for member, text in members:
                    zipf.writestr(member, text)

        output_file = Path(output_path).expanduser()
        try:
            # Create output directory if needed (direct callers; the
            # tool refuses a folder that does not exist)
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Failed to export to REFI-QDA: %s", error_label(e))
            raise RuntimeError(
                f"REFI-QDA export failed: {error_text(e)}") from None
        logger.info("Creating a .qdpx archive")
        self.counts["part_files_removed"] = write_beside_and_replace(
            output_file, fill, overwrite)
        logger.info("Exported %s coding(s) and %s text source(s) to a .qdpx "
                    "archive", len(suggestions),
                    self.counts.get("text_sources", 0))
        return str(output_file)

    def validate_suggestions(
            self, suggestions: List[CodingSuggestion],
            texts: Optional[Dict[int, Optional[Dict[str, Any]]]] = None
    ) -> List[str]:
        """Validate suggestions before export.

        Args:
            suggestions: List of suggestions to validate
            texts: Texts already read, by file id; each other text the
                check needs is read once and kept there

        Returns:
            List of validation warnings/errors (empty if all valid)

        Raises:
            RuntimeError: a read of the project failed, in words naming
                the kind of row (`read_for_export`)
        """
        warnings = []
        texts = texts if texts is not None else {}

        # Check if we have any suggestions
        if not suggestions:
            warnings.append("No suggestions to export")
            return warnings

        # Every code and file of the project, each read worded by its kind
        # of row when it fails, as the export's other reads are: the
        # export stops before anything is written
        code_ids = {c["id"] for c in read_for_export(
            "codes and categories", self.db.list_codes)}
        file_ids = {f["id"] for f in read_for_export(
            "text sources", self.db.list_files)}

        # File text lengths (also identifies files with no exportable text)
        content_lengths: Dict[int, int] = {}

        # Validate each suggestion
        for i, suggestion in enumerate(suggestions):
            # Named by its place counted from 1, as review_suggestions
            # counts, and by its GUID, which every session tool takes
            which = f"Suggestion {i + 1}" + (
                f" (GUID {suggestion.guid})"
                if getattr(suggestion, "guid", None) else "")
            # Check code exists
            if suggestion.code_id not in code_ids:
                warnings.append(
                    f"{which}: Code ID {suggestion.code_id} not found in project"
                )

            # Check file exists
            if suggestion.file_id not in file_ids:
                warnings.append(
                    f"{which}: File ID {suggestion.file_id} not found in project"
                )
            else:
                if suggestion.file_id not in content_lengths:
                    fc = self._text(suggestion.file_id, texts)
                    content = (fc or {}).get("content") or ""
                    content_lengths[suggestion.file_id] = len(content)
                    if content and len(content.encode("utf-8")) > _MAX_INTERNAL_FILE_BYTES:
                        warnings.append(
                            f"File {suggestion.file_id} exceeds the REFI-QDA "
                            f"2 GiB internal file limit"
                        )
                length = content_lengths[suggestion.file_id]
                if length == 0:
                    warnings.append(
                        f"{which}: File ID {suggestion.file_id} has no "
                        f"text content; selections cannot be exported for it"
                    )
                elif isinstance(suggestion.end_pos, int) and suggestion.end_pos > length:
                    warnings.append(
                        f"{which}: End position {suggestion.end_pos} is "
                        f"beyond the file text (length {length})"
                    )

            # Check positions are valid. Damaged projects can carry rows with
            # NULL positions (QA2-6) — report them, never TypeError on them.
            if (not isinstance(suggestion.start_pos, int)
                    or isinstance(suggestion.start_pos, bool)
                    or not isinstance(suggestion.end_pos, int)
                    or isinstance(suggestion.end_pos, bool)):
                warnings.append(
                    f"{which}: missing or non-integer positions "
                    f"(start={suggestion.start_pos!r}, end={suggestion.end_pos!r}) "
                    f"; the coding row may be damaged"
                )
                continue

            if suggestion.start_pos < 0:
                warnings.append(
                    f"{which}: Invalid start position {suggestion.start_pos}"
                )

            if suggestion.end_pos <= suggestion.start_pos:
                warnings.append(
                    f"{which}: End position {suggestion.end_pos} must be greater than start position {suggestion.start_pos}"
                )

        return warnings


def _unset(value: Any) -> bool:
    """An attribute value that is not set: NULL or empty."""
    return value is None or (isinstance(value, str) and value == "")


def _value_text(value: Any, numeric: bool) -> Optional[str]:
    """What a VariableValue holds for a stored value: a numeric
    attribute's value in plain decimal notation when `finite_number` reads
    it as a number (it and QualCoder's `float` read the same number), else
    None, left out; a text attribute's value as it is."""
    if isinstance(value, bytes):
        text = value.decode("utf-8", "replace")
    else:
        text = value if isinstance(value, str) else str(value)
    if not numeric:
        return _xml_safe(text)
    number = finite_number(text)
    return None if number is None else plain_decimal(number)
