# SPDX-License-Identifier: LGPL-3.0-or-later
"""Bringing documents into a project from the researcher's computer, the
way QualCoder's own import does (0.14.3; the import and
reading design, Parts 3 to 6).

The server's `import_documents` tool calls `survey` twice: once for the
preview, which reads every file (in a reading process) and writes
nothing, and once with the token, to check that nothing has changed
before anything is written. `write_batch` then copies the originals into
the project's folder of originals and stores their text, inside the
server's usual write discipline (the gate, the lock, the backup, one
transaction).

The text is QualCoder 4.0's (doc_readers); what is not QualCoder's is a
named departure, listed in TOOLS.md. Plain text and web pages are read
as UTF-8 alone, and a file that is not UTF-8 is held back with steps to
save it so: nothing is guessed (the owner's decision of 6 October 2026),
so the names list is applied to, and checked in, the text as it is
stored.
"""

import hashlib
import os
import secrets
import stat
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import doc_readers, garbled_text, import_paths, import_reading
from . import import_words as words

MAX_PATHS = 50
MAX_BATCH = 50
MAX_MEMO = 10_000
# How long one call may read (provisional, 0.14.3): a host can stop a
# tool call that runs long (Claude Desktop's own text is said to give
# 180 seconds, and 60 to a local server added by hand; not yet timed), so
# each call stops between files within these, counted from the call's
# start, and says how to go on with the rest. The preview reads for 30
# seconds, so that the import, which reads the same files again from
# their copies, fits within its own 45; one file read at the import has
# 40 seconds (the preview's 30 for a file, and a margin), and the first
# file a call reads always has its whole time, so each call takes in at
# least one file.
PREVIEW_SECONDS = 30
IMPORT_SECONDS = 45
IMPORT_FILE_SECONDS = 40
# Less time than this left in a call: no file is started.
LEAST_SECONDS = 1.0


def clock() -> float:
    """The clock a call's time is counted by."""
    return time.monotonic()
MB = 1024 * 1024
# One file on the disk, by format (the design's Part 5).
SIZE_LIMITS = {
    doc_readers.TEXT: 8 * MB, doc_readers.MARKDOWN: 8 * MB,
    doc_readers.SUBTITLES: 8 * MB, doc_readers.WEB: 32 * MB,
    doc_readers.RTF: 32 * MB, doc_readers.WORD: 100 * MB,
    doc_readers.OPENDOCUMENT: 100 * MB, doc_readers.EPUB: 100 * MB,
    doc_readers.PDF: 100 * MB,
}
# What an interrupted import leaves in the folder of originals, so that
# the next import recognises and removes it.
TEMP_PREFIX = ".exegete-importing-"
ORDINALS = ("first", "second", "third", "fourth", "fifth", "sixth",
            "seventh", "eighth", "ninth", "tenth")


def ordinal(n: int) -> str:
    if 1 <= n <= len(ORDINALS):
        return ORDINALS[n - 1]
    suffix = ("th" if 10 <= n % 100 <= 20
              else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))
    return f"{n}{suffix}"


@dataclass
class Item:
    """One file the batch names, from first look to the row it becomes."""
    order: int
    given: int
    path: Path
    disk_name: str
    kind: Optional[str]
    position: str
    name: str = ""
    hide_name: bool = False
    listed_name_in_name: bool = False   # let through on the researcher's word
    size: int = 0
    digest: str = ""
    status: str = "ready"          # ready, refused, held, skipped, later
    # A file left for the next call ("later"): code "" when the batch
    # already holds MAX_BATCH new files, NOT_READ_THIS_TIME when the
    # preview's time ran out before it was read, NOT_IMPORTED_THIS_TIME
    # when the import's did.
    code: str = ""
    numbers: Dict[str, Any] = field(default_factory=dict)
    read: Optional[Dict[str, Any]] = None
    text: str = ""
    replacements: int = 0
    memo: str = ""
    warnings: List[Tuple[str, str]] = field(default_factory=list)
    warning_codes: List[str] = field(default_factory=list)
    real_place: Optional[str] = None
    # Letters that look garbled: the text as it would be stored, and the
    # places in it, for the page the researcher can check them on.
    check_text: Optional[str] = None
    check_places: List[Any] = field(default_factory=list)

    pre_code: str = ""             # a refusal decided before reading

    def fingerprint(self) -> List[Any]:
        """What the token binds for this file: where it is, the name it
        would have, its size and digest, and any refusal decided before
        its text was read (those after follow from the bytes)."""
        if self.status == "later":
            return [self.given, str(self.path), "later"]
        return [self.given, str(self.path), self.name, self.size,
                self.digest, self.pre_code]


@dataclass
class Context:
    """What a survey needs to know about the project and the call."""
    project_folder: Path
    source_names: Dict[str, Optional[str]]   # name -> stored path
    documents_listing: List[str]
    refused_places: Sequence[Tuple[str, Optional[Path]]]
    compiled: Any = None                     # the names list, compiled
    # What file and folder names are checked against, when it is not the
    # compiled list: a list Exegete cannot use still holds names (as far
    # as they can be read; every name counts as holding one when none
    # can), so that the preview of an import it stops shows none of them.
    name_check: Any = None
    names_list: str = "none"         # none, empty, entries, off, unusable
    names_list_entries: int = 0
    names_list_canonical: Any = None
    optional_available: frozenset = frozenset()   # PDF, EPUB readable
    qc382: bool = False
    pdfs_with_listed_names: bool = False
    file_names_with_listed_names: bool = False
    # The researcher's word that files whose letters look garbled come in
    # as they are (the owner's ruling of 7 October 2026).
    files_with_garbled_letters: bool = False
    max_characters: int = 1_000_000
    # The reader: None for the reading process (import_reading's
    # read_in_process, looked up at each read).
    reader: Optional[Callable[..., Dict[str, Any]]] = None
    # When the tool call began (clock()), from which its time is counted;
    # None: when the survey or the write begins.
    call_started: Optional[float] = None
    preview_seconds: float = PREVIEW_SECONDS
    import_seconds: float = IMPORT_SECONDS
    home: Optional[Path] = None
    memo: str = ""


def stored_name(disk_name: str) -> str:
    """The one form of a name used for the row, the stored path and the
    copy: Unicode's composed form, the ends trimmed."""
    return unicodedata.normalize("NFC", disk_name.strip())


def shown_name(name: str, limit: int = 120) -> str:
    """A file name as an answer may show it: control and invisible
    characters made visible, cut to a fixed length."""
    out = []
    for ch in name:
        category = unicodedata.category(ch)
        if category in ("Cc", "Cf", "Zl", "Zp") or ch in "  ":
            out.append(f"<U+{ord(ch):04X}>")
        else:
            out.append(ch)
    text = "".join(out)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def name_holds_listed_name(compiled: Any, name: str) -> bool:
    """Whether a file's (or a folder's) name holds a name from the list,
    by Exegete's one rule for a name inside a name (pseudonymise's
    `carries_a_name`): in any letter case, across any separator, inside
    a longer word too, so that `Maria_interview.docx`,
    `maria-interview.docx` and `MariaB.docx` are all caught. Wider than
    the rule that replaces names in the text, on purpose: a name held
    back in error costs a rename or the researcher's word; one let
    through reaches the AI provider in every answer that names the
    file."""
    return compiled is not None and compiled.carries_a_name(name)


def _name_check(ctx: "Context") -> Any:
    return ctx.name_check if ctx.name_check is not None else ctx.compiled


class EveryName:
    """A names list that cannot be read at all: every file and folder
    name is taken to hold a name from it, so the preview shows none."""

    @staticmethod
    def carries_a_name(value: Any) -> bool:
        return isinstance(value, str) and bool(value)


class OriginalsOnly:
    """The names of a list Exegete cannot use (a name with a space at its
    end, a pseudonym the engine refuses, a chain), read for the one
    question of whether a file's or folder's name holds one, by the same
    wide reading as for a usable list."""

    def __init__(self, forms: Sequence[str]):
        from .pseudonymise import NameDetector
        self.detector = NameDetector(forms)

    def carries_a_name(self, value: Any) -> bool:
        return self.detector.contains(value)


@dataclass
class Survey:
    items: List[Item] = field(default_factory=list)
    path_refusals: List[Dict[str, Any]] = field(default_factory=list)
    folders: List[Dict[str, Any]] = field(default_factory=list)

    def left_for_later(self, code: str) -> List[Item]:
        return [i for i in self.items
                if i.status == "later" and i.code == code]

    def fingerprint(self, ctx: Context) -> Dict[str, Any]:
        return {
            "items": [item.fingerprint() for item in self.items],
            "read_outcomes": [entry[:3] for entry in read_outcomes(self)],
            "paths": [[r["given"], r["code"]] for r in self.path_refusals],
            "folders": [[f["given"], f["files"]] for f in self.folders],
            "project_names": sorted(ctx.source_names),
            "documents": sorted(ctx.documents_listing),
            "names_list": [ctx.names_list, ctx.names_list_canonical],
        }


# ---------------------------------------------------------------------------
# What the preview's reading decided, kept for the import
# ---------------------------------------------------------------------------

# The files the preview held back or refused once it had read them, by
# the preview's token, so that the import skips exactly those and a file
# the preview called ready either goes in or stops the whole batch. The
# token's signed state binds the same list, so what is kept here can only
# be the preview's own; when it is not here (the server restarted since
# the preview), a preview that held back or refused a file after reading
# it no longer matches, and the import asks for a fresh preview.
_PREVIEW_OUTCOMES: "Dict[str, List[List[Any]]]" = {}
_KEEP_OUTCOMES = 64


def read_outcomes(result: "Survey") -> List[List[Any]]:
    """[order, status, code, numbers] for every file held back or refused
    after its text was read, and every file the preview's time left for
    the next call (a decision made before reading is in the file's own
    fingerprint)."""
    return [[item.order, item.status, item.code, dict(item.numbers)]
            for item in result.items
            if (item.status in ("held", "refused") and not item.pre_code)
            or (item.status == "later" and item.code == NOT_READ_THIS_TIME)]


def remember_outcomes(token: str, result: "Survey") -> None:
    _PREVIEW_OUTCOMES[token] = read_outcomes(result)
    while len(_PREVIEW_OUTCOMES) > _KEEP_OUTCOMES:
        _PREVIEW_OUTCOMES.pop(next(iter(_PREVIEW_OUTCOMES)))


def apply_outcomes(result: "Survey", token: Any) -> None:
    """Give the import's survey (which reads no text) the preview's own
    decisions on the files it held back or refused after reading them."""
    kept = _PREVIEW_OUTCOMES.get(token) if isinstance(token, str) else None
    by_order = {entry[0]: entry for entry in (kept or [])}
    for item in result.items:
        entry = by_order.get(item.order)
        if entry is None or item.status != "ready":
            continue
        item.status, item.code = entry[1], entry[2]
        item.numbers.update(entry[3])


def forget_outcomes(token: Any) -> None:
    if isinstance(token, str):
        _PREVIEW_OUTCOMES.pop(token, None)


def _supported_suffixes() -> List[str]:
    return sorted(doc_readers.FORMATS)


def _hidden_in_listing(name: str, ctx: Context) -> bool:
    return name_holds_listed_name(_name_check(ctx), stored_name(name))


HIDDEN_STEP = "(a name from your names list)"


def shown_place(place: Optional[str], ctx: Context) -> Optional[str]:
    """A place on the computer (where a link leads) as the preview may
    show it: each step that holds a name from the list replaced by
    words saying so."""
    if not place:
        return place
    check = _name_check(ctx)
    if check is None:
        return place
    windows = "\\" in place and "/" not in place
    steps = place.replace("\\", "/").split("/")
    hidden = [bool(step) and name_holds_listed_name(check, stored_name(step))
              for step in steps]
    if not any(hidden):
        return place
    return ("\\" if windows else "/").join(
        HIDDEN_STEP if hide else step for step, hide in zip(steps, hidden))


def gather(paths: Sequence[str], ctx: Context) -> Survey:
    """Walk every given path and list every given folder: the files the
    batch names, in order, before any is opened."""
    survey = Survey()
    order = 0
    for given, text in enumerate(paths, start=1):
        try:
            walked = import_paths.walk(text, ctx.refused_places, ctx.home)
        except import_paths.PathRefused as refused:
            survey.path_refusals.append({"given": given, "code": refused.code})
            continue
        place = shown_place(walked.real_place, ctx)
        if not walked.is_folder:
            order += 1
            disk_name = walked.path.name
            survey.items.append(Item(
                order=order, given=given, path=walked.path,
                disk_name=disk_name,
                kind=doc_readers.FORMATS.get(
                    os.path.splitext(disk_name)[1].lower()),
                position=f"the file given as path {given}",
                real_place=place))
            continue
        try:
            listing = import_paths.list_folder(
                walked.path, _supported_suffixes(),
                words.KNOWN_OTHER_SUFFIXES)
        except import_paths.PathRefused as refused:
            survey.path_refusals.append({"given": given, "code": refused.code})
            continue
        folder = {"given": given, "files": list(listing.files),
                  "real_place": place,
                  "subfolders": [], "other_formats": [],
                  "links": [], "not_files": [],
                  "hidden_skipped": listing.hidden_skipped,
                  "unsupported": listing.unsupported,
                  "stopped_early": listing.stopped_early}
        for index, name in enumerate(listing.files, start=1):
            order += 1
            survey.items.append(Item(
                order=order, given=given, path=walked.path / name,
                disk_name=name,
                kind=doc_readers.FORMATS.get(os.path.splitext(name)[1].lower()),
                position=f"the {ordinal(index)} document in the folder "
                         f"given as path {given}, counting only the kinds "
                         f"Exegete imports, in A to Z order (P10 before "
                         f"P2)",
                real_place=place))
        for key, names in (("links", listing.links),
                           ("not_files", listing.not_files),
                           ("other_formats", listing.other_formats)):
            for name in names:
                folder[key].append(
                    HIDDEN_STEP
                    if _hidden_in_listing(name, ctx) else shown_name(name))
        for name, count in listing.subfolders:
            folder["subfolders"].append({
                "name": (HIDDEN_STEP
                         if _hidden_in_listing(name, ctx)
                         else shown_name(name)),
                "supported_files": count})
        survey.folders.append(folder)
    return survey


class _ReadRefusal(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _dataless(info: os.stat_result) -> bool:
    """A cloud drive's placeholder for a file kept online only."""
    flags = getattr(info, "st_flags", 0)
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(flags & 0x40000000) or bool(attributes & (0x400000 | 0x1000))


def read_bytes(path: Path, limit: int) -> Tuple[bytes, int]:
    """The file's bytes, opened once without following a link, or a
    refusal code. (data, size); data is None when the file is over
    `limit`, which is checked from its size before anything is read."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(
        os, "O_BINARY", 0)
    try:
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise _ReadRefusal("not_a_file")
        fd = os.open(path, flags)
    except _ReadRefusal:
        raise
    except PermissionError:
        raise _ReadRefusal("permission") from None
    except OSError:
        raise _ReadRefusal("unreadable") from None
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise _ReadRefusal("not_a_file")
        if opened.st_size > limit:
            return None, opened.st_size
        chunks = []
        remaining = opened.st_size + 1
        while remaining > 0:
            try:
                chunk = os.read(fd, min(remaining, 4 * MB))
            except OSError:
                raise _ReadRefusal("online_only" if _dataless(info)
                                   else "unreadable") from None
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) != opened.st_size:
            raise _ReadRefusal("changed_while_read")
        return data, opened.st_size
    finally:
        os.close(fd)


def digest_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _refuse(item: Item, code: str, before_reading: bool = True,
            **numbers: Any) -> None:
    item.status = "refused"
    item.code = code
    item.numbers.update(numbers)
    if before_reading:
        item.pre_code = code


def _same_original(ctx: Context, name: str, digest: str, size: int) -> bool:
    try:
        data, _size = read_bytes(ctx.project_folder / "documents" / name,
                                 size)
    except _ReadRefusal:
        return False
    return data is not None and digest_of(data) == digest


def prepare(item: Item, ctx: Context, seen_keys: set,
            new_so_far: int) -> Optional[bytes]:
    """Every check on one file that needs no reading of its text; the
    file's bytes when it is to be read, else None (its status says
    why)."""
    from .database import documents_name_key, file_name_problem
    suffix = os.path.splitext(item.disk_name)[1].lower()
    item.name = stored_name(item.disk_name)
    check = _name_check(ctx)
    if isinstance(check, EveryName):
        # A names list that cannot be read: the import is stopped, and no
        # file is shown by its name.
        item.hide_name = True
    elif name_holds_listed_name(check, item.name):
        if not ctx.file_names_with_listed_names:
            # Held back, and referred to by its position only, so that
            # the name does not reach the provider in the preview.
            item.hide_name = True
            item.status, item.code = "held", "names_in_file_name"
            item.pre_code = item.code
            return None
        # The researcher's word: it comes in under its name, and the
        # preview and the answer say so.
        item.listed_name_in_name = True
    if item.kind is None:
        _refuse(item, "other_format" if suffix in words.OTHER_FORMATS
                else "unsupported", suffix=suffix)
        return None
    if (item.kind in doc_readers.OPTIONAL_FORMATS
            and item.kind not in ctx.optional_available):
        _refuse(item, "optional_missing")
        return None
    problem = file_name_problem(item.name)
    if problem is not None:
        _refuse(item, "name_rule", problem=problem)
        return None
    key = documents_name_key(item.name)
    if key in seen_keys:
        _refuse(item, "same_name_in_batch")
        return None
    seen_keys.add(key)
    in_project = item.name in ctx.source_names
    clash = [entry for entry in ctx.documents_listing
             if documents_name_key(entry) == key]
    if not in_project and clash:
        owner = next((row for row, stored in ctx.source_names.items()
                      if stored == "/docs/" + clash[0] and row != clash[0]),
                     None)
        _refuse(item, "documents_clash", entry=shown_name(clash[0]),
                owner=shown_name(owner) if owner else None)
        return None
    if not in_project and new_so_far >= MAX_BATCH:
        item.status = "later"
        return None
    try:
        data, size = read_bytes(item.path, SIZE_LIMITS[item.kind])
    except _ReadRefusal as refusal:
        _refuse(item, refusal.code)
        return None
    item.size = size
    if data is None:
        _refuse(item, "too_large",
                limit_mb=SIZE_LIMITS[item.kind] // MB)
        return None
    item.digest = digest_of(data)
    if in_project:
        if (ctx.source_names[item.name] == "/docs/" + item.name
                and _same_original(ctx, item.name, item.digest, size)):
            item.status, item.code = "skipped", "already_there"
            item.pre_code = item.code
        else:
            _refuse(item, "name_in_use")
        return None
    return data


def evaluate(item: Item, result: Dict[str, Any], ctx: Context) -> None:
    """What the import does with one file's text: holds it back, or
    applies the names list and gathers its warnings and memo. The text is
    the one that will be stored (UTF-8 alone, for plain text and web
    pages), so the names found in it are the names there are."""
    from . import pseudonymise as pseudo
    item.read = result
    text = result["text"]
    signs = dict(result["signs"])
    notes = result["notes"]
    if item.kind == doc_readers.PDF:
        found = []
        if ctx.compiled is not None:
            found = pseudo.find_replacements(ctx.compiled, text)
            if notes:
                found += pseudo.find_replacements(
                    ctx.compiled, "\n".join(n["content"] for n in notes))
        if found:
            item.numbers["listed_names"] = len({r.entry for r in found})
            item.numbers["listed_count"] = len(found)
            if not ctx.pdfs_with_listed_names:
                item.status, item.code = "held", "pdf_listed_names"
                return
    elif ctx.compiled is not None:
        replacements = pseudo.find_replacements(ctx.compiled, text)
        text = pseudo.apply_replacements(text, replacements)
        item.replacements = len(replacements)
    if len(text) > ctx.max_characters:
        _refuse(item, "too_long", before_reading=False,
                characters=len(text), limit=ctx.max_characters)
        return
    if signs.get("garbled"):
        # Letters that look garbled ("Ã©" for "é"): a name written so
        # would escape the list. The researcher decides, having been told
        # what was seen and offered a page to check it on.
        _garbled_seen(item, result["text"], text)
        item.code = ("garbled_rtf" if item.kind == doc_readers.RTF
                     and signs.get("rtf_raw_utf8") else "garbled_fixed")
        if not ctx.files_with_garbled_letters:
            item.status = "held"
            return
        item.code = ""
    item.text = text
    item.status = "ready"
    item.warnings = _warnings(item, result, signs, ctx, len(text))
    item.memo = _memo(item, result, ctx)


def _garbled_seen(item: Item, read: str, stored: str) -> None:
    """What the preview says of letters that look garbled, and what the
    page to check them shows: the places in the text as it would be
    stored (in the text as read, should the names list have changed
    every one), how many, the first one's line, the sets they read back
    through."""
    found = garbled_text.places(stored)
    item.check_text, item.check_places = stored, found
    if not found:
        found = garbled_text.places(read)
        stored = read
    if not found:
        return
    counted: Dict[str, int] = {}
    for place in found:
        if place.set_name is not None:
            counted[place.set_name] = counted.get(place.set_name, 0) + 1
    order = sorted(counted, key=lambda name: (-counted[name],
                                              list(counted).index(name)))
    item.numbers.update({
        "where": words.where_phrase(
            len(found), stored.count("\n", 0, found[0].start) + 1,
            garbled_text.MAX_PLACES),
        "sets": words.sets_phrase(
            [garbled_text.SET_NAMES[name] for name in order[:2]],
            len(order) > 2),
        "lost": sum(1 for place in found if place.set_name is None)})


def _warnings(item: Item, result: Dict[str, Any], signs: Dict[str, int],
              ctx: Context, characters: int) -> List[Tuple[str, str]]:
    """The file's warnings, in Exegete's fixed words, each with its
    group: "changes" (what the researcher will read) or "information"."""
    out: List[Tuple[str, str]] = []

    def add(code: str, **numbers: Any) -> None:
        group = words.WARNINGS[code][0]
        out.append((group, words.say(words.WARNINGS, code, **numbers)))
        item.warning_codes.append(code)

    for code in (doc_readers.WORD_DEPARTURES + ("word_revisions",)
                 + doc_readers.ODT_DEPARTURES + ("odt_tables",)
                 + doc_readers.RTF_DEPARTURES + doc_readers.WEB_DEPARTURES
                 + ("pdf_scanned", "pandoc_wrapped", "pandoc_tables",
                    "pandoc_notes", "subtitles")):
        if signs.get(code):
            add(code, count=signs[code])
    if any(signs.get(code) for code in doc_readers.DEPARTURES):
        # Said once, after the departures' own lines.
        add(words.READS_OTHERWISE)
    if characters > ctx.max_characters // 2:
        add("near_limit", characters=characters, limit=ctx.max_characters)
    for code in ("astral", "invisible"):
        if signs.get(code):
            add(code, count=signs[code])
    if signs.get("spaces_only"):
        add("spaces_only")
    if signs.get("pdf_notes"):
        add("pdf_notes", count=signs["pdf_notes"])
    if signs.get("pdf_markups"):
        add("pdf_markups", count=signs["pdf_markups"])
    if item.kind == doc_readers.PDF and ctx.qc382:
        add("qc382_pdf")
    if item.listed_name_in_name:
        add("listed_name_in_file_name")
    if item.check_text is not None:
        add("garbled_letters", where=item.numbers.get("where", "in places"))
    return out


def _memo(item: Item, result: Dict[str, Any], ctx: Context) -> str:
    """The file's memo: the memo argument, then the PDF's notes after a
    blank line, as QualCoder orders them."""
    memo = ctx.memo or ""
    if result["notes"]:
        notes = doc_readers.pdf_notes_memo(result["notes"])
        memo = memo + "\n\n" + notes if memo else notes
    return memo


# What the reader refuses that the import holds back, with the steps to
# a file it reads: one not saved as UTF-8.
GARBLED = frozenset({"garbled_fixed", "garbled_rtf"})
HELD_WHEN_READ = frozenset({"not_utf8", "not_utf8_web", "nul_characters",
                            "nul_characters_web"})
NOT_READ_THIS_TIME = "not_read_this_time"
NOT_IMPORTED_THIS_TIME = "not_imported_this_time"


def _time_for(limit: float, budget: float, started: float, first: bool,
              now: Callable[[], float]) -> Optional[float]:
    """How long the next file may be read: its whole `limit` when it is
    the call's first, else no more than what is left of the call's
    `budget`; None when too little is left to start one."""
    if first:
        return limit
    left = budget - (now() - started)
    if left < LEAST_SECONDS:
        return None
    return min(limit, left)


def _read_one(item: Item, data: bytes, ctx: Context,
              timeout: Optional[float] = None,
              limit: Optional[float] = None,
              later_code: str = NOT_READ_THIS_TIME) -> None:
    """Read one file's text in the reading process. A read stopped by
    what was left of the call's time, short of the file's own `limit`,
    leaves the file for the next call (`later_code`); one stopped at its
    own limit refuses it."""
    limit = import_reading.READ_TIMEOUT_SECONDS if limit is None else limit
    timeout = limit if timeout is None else timeout
    reader = ctx.reader or import_reading.read_in_process
    try:
        result = reader(item.kind, data, max_characters=ctx.max_characters,
                        timeout=timeout)
    except import_reading.ReadFailed as failed:
        if failed.code in HELD_WHEN_READ:
            item.status, item.code = "held", failed.code
            return
        if failed.code == "reader_timeout" and timeout < limit:
            item.status, item.code = "later", later_code
            return
        numbers = dict(failed.numbers)
        if "limit" in numbers and failed.code.startswith("archive_part") \
                or failed.code == "archive_too_large":
            numbers["limit_mb"] = numbers.get("limit", 0) // MB
        if failed.code == "reader_timeout":
            numbers["seconds"] = int(limit)
        if failed.code == "reader_memory":
            numbers["limit_mb"] = import_reading.MEMORY_CAP_BYTES // MB
        _refuse(item, failed.code, before_reading=False, **numbers)
        return
    evaluate(item, result, ctx)


def survey(paths: Sequence[str], ctx: Context, read_texts: bool = True,
           now: Optional[Callable[[], float]] = None) -> Survey:
    """The batch as the preview sees it. With `read_texts` false (the
    import's check of its token), files are hashed but not read.

    The preview reads for `ctx.preview_seconds` from the call's start: a
    file it has no time left for is left for the next call (status
    "later"), and so is one whose reading the time left cut short; the
    first file read always has its whole time."""
    now = now or clock
    result = gather(paths, ctx)
    seen: set = set()
    new_so_far = 0
    started = ctx.call_started if ctx.call_started is not None else now()
    first = True
    for item in result.items:
        data = prepare(item, ctx, seen, new_so_far)
        if data is None:
            continue
        new_so_far += 1
        if not read_texts:
            continue
        timeout = _time_for(import_reading.READ_TIMEOUT_SECONDS,
                            ctx.preview_seconds, started, first, now)
        if timeout is None:
            item.status, item.code = "later", NOT_READ_THIS_TIME
            continue
        first = False
        _read_one(item, data, ctx, timeout)
    return result


# ---------------------------------------------------------------------------
# What the preview says, in this order, never with any of the text
# ---------------------------------------------------------------------------

def item_label(item: Item) -> str:
    return item.position if item.hide_name else shown_name(item.name
                                                           or item.disk_name)


def refusal_words(item: Item) -> str:
    code, numbers = item.code, dict(item.numbers)
    if code == "other_format":
        return words.OTHER_FORMATS.get(numbers.get("suffix", ""),
                                       words.FILE_REFUSALS["unsupported"])
    if code == "name_rule":
        return (f"Its name cannot be used in a project: "
                f"{numbers.get('problem', '')} Rename the file on your "
                f"computer, then ask again.")
    if code == "documents_clash":
        text = (f"The project's folder of originals already holds "
                f"'{numbers.get('entry')}', the same name on a disk that "
                f"ignores letter case.")
        if numbers.get("owner"):
            text += (f" It is the original of the file now called "
                     f"'{numbers['owner']}'.")
        return text + " Rename this file on your computer, then ask again."
    if code in ("permission", "unreadable", "not_a_file"):
        return words.PATH_REFUSALS[code]
    if code in GARBLED:
        return words.garbled_words(code, numbers)
    if code in words.HELD_BACK:
        people = numbers.get("listed_names") or 0
        times = numbers.get("listed_count") or 0
        return words.say(
            words.HELD_BACK, code,
            people=f"{people} {'person' if people == 1 else 'people'}",
            times="once" if times == 1 else f"{times} times")
    numbers.setdefault("format", {
        doc_readers.WORD: "Word", doc_readers.OPENDOCUMENT: "OpenDocument",
        doc_readers.EPUB: "EPUB"}.get(item.kind, "document"))
    return words.say(words.FILE_REFUSALS, code, **numbers)


def names_list_line(ctx: Context) -> str:
    if ctx.names_list == "none":
        return ("This project has no list of names to replace. If these "
                "documents name participants or places, make the list "
                "first (QualCoder's Pseudonyms dialog); the import then "
                "replaces the names as the text comes in.")
    if ctx.names_list == "empty":
        return ("This project's list of names to replace is empty, so no "
                "names are replaced.")
    if ctx.names_list == "off":
        return ("The project's list of names is not applied to this "
                "import, as asked: the real names are stored, and PDFs "
                "and file names holding names from it are not held back.")
    if ctx.names_list == "unusable":
        return ("The project's list of names cannot be used as it stands "
                "(what stops the import says why), so nothing is imported "
                "until it is corrected. Meanwhile every file and folder "
                "whose name may hold a name from it is shown by its "
                "position only.")
    return (f"The project's list of names ({ctx.names_list_entries} "
            f"entries) is applied to the text as it comes in (never to "
            f"PDFs, nor to the originals).")


def file_entry(item: Item) -> Dict[str, Any]:
    result = item.read or {}
    entry: Dict[str, Any] = {
        "file": item_label(item),
        "format": item.kind,
        "size_kb": round(item.size / 1024, 1),
        "words": len(item.text.split()),
    }
    if result.get("charset") in ("utf-8", "utf-8-sig"):
        # Plain text and web pages: the one character set read.
        entry["character_set"] = "UTF-8"
    if item.kind != doc_readers.PDF and item.replacements:
        entry["names_replaced"] = item.replacements
    if item.numbers.get("listed_count"):
        entry["listed_names_kept"] = item.numbers["listed_count"]
    changes = [text for group, text in item.warnings if group == "changes"]
    information = [text for group, text in item.warnings
                   if group == "information"]
    if changes:
        entry["changes_what_you_will_read"] = changes
        entry["why"] = words.why_line(item.kind == doc_readers.SUBTITLES,
                                      item.warning_codes)
    if information:
        entry["for_information"] = information
    if item.real_place:
        entry["real_place"] = item.real_place
    return entry


def summary_line(ready: int, look: int, held: int, refused: int,
                 skipped: int, unread: int = 0) -> str:
    parts = [f"{ready} file{'s' if ready != 1 else ''} ready"]
    if look:
        parts.append(f"{look} need{'s' if look == 1 else ''} a look before "
                     f"you say yes")
    if held:
        parts.append(f"{held} held back")
    if refused:
        parts.append(f"{refused} refused")
    if skipped:
        parts.append(f"{skipped} already in the project")
    if unread:
        # Said in the line the researcher is shown, so that a batch the
        # preview's time cut short is never taken for the whole of it.
        parts.append(f"{unread} not read this time")
    return "; ".join(parts) + "."


def preview_answer(result: Survey, ctx: Context,
                   stops: Sequence[str] = (),
                   backup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The preview, in the order the design gives: what stops the whole
    import, the summary line, the names list, files held back, each
    file, the batch, and a closing line."""
    ready = [i for i in result.items if i.status == "ready"]
    held = [i for i in result.items if i.status == "held"]
    refused = [i for i in result.items if i.status == "refused"]
    skipped = [i for i in result.items if i.status == "skipped"]
    later = result.left_for_later("")
    unread = result.left_for_later(NOT_READ_THIS_TIME)
    look = sum(1 for i in ready if any(g == "changes" for g, _ in i.warnings))
    answer: Dict[str, Any] = {}
    if stops:
        answer["stops_the_import"] = list(stops)
    answer["summary"] = summary_line(len(ready), look, len(held),
                                     len(refused) + len(result.path_refusals),
                                     len(skipped), len(unread))
    answer["names_list"] = names_list_line(ctx)
    if held:
        answer["held_back"] = [{"file": item_label(i),
                                "reason": refusal_words(i)} for i in held]
    answer["files"] = [file_entry(i) for i in ready]
    if refused or result.path_refusals:
        answer["refused"] = (
            [{"path": r["given"],
              "reason": words.PATH_REFUSALS.get(
                  r["code"], words.PATH_REFUSALS["unreadable"])}
             for r in result.path_refusals]
            + [{"file": item_label(i), "reason": refusal_words(i)}
               for i in refused])
    if skipped:
        answer["already_in_the_project"] = [item_label(i) for i in skipped]
    if later:
        answer["not_taken_this_time"] = (
            f"{len(later)} more file{'s' if len(later) != 1 else ''} in the "
            f"folder are not in this batch: at most {MAX_BATCH} files not "
            f"yet in the project are taken at a time, by name. After this "
            f"import, ask again with the same folder for the next ones.")
    if unread:
        answer["not_read_this_time"] = {
            "files": [item_label(i) for i in unread],
            "note": not_read_note(len(unread), bool(ready),
                                  bool(held or refused)),
        }
    folders = []
    for folder in result.folders:
        note: Dict[str, Any] = {"path": folder["given"]}
        if folder["real_place"]:
            note["real_place"] = folder["real_place"]
        if folder["subfolders"]:
            note["subfolders_not_opened"] = folder["subfolders"]
            note["subfolders_note"] = ("Folders inside are not opened; to "
                                       "bring their files in, name them "
                                       "too.")
        if folder["other_formats"]:
            note["other_documents"] = folder["other_formats"]
            note["other_documents_note"] = (
                "Files of kinds Exegete does not import: .doc, save as "
                ".docx in Word; .pages, export to Word in Pages; .gdoc, "
                "download as Word from Google Docs.")
        if folder["links"]:
            note["links_refused"] = folder["links"]
        if folder["not_files"]:
            note["not_ordinary_files"] = folder["not_files"]
        if folder["hidden_skipped"]:
            note["hidden_files_skipped"] = folder["hidden_skipped"]
        if folder["unsupported"]:
            note["other_files_ignored"] = folder["unsupported"]
        if folder["stopped_early"]:
            note["stopped_early"] = (
                f"The folder holds more than "
                f"{import_paths.MAX_FOLDER_ENTRIES} entries; only the first "
                f"were looked at. Give a smaller folder.")
        if len(note) > 1:
            folders.append(note)
    if folders:
        answer["folders"] = folders
    batch: Dict[str, Any] = {
        "files_in": len(ready), "refused": len(refused)
        + len(result.path_refusals), "held_back": len(held),
        "already_in_the_project": len(skipped),
        "originals_go_to": "the project's own folder of originals "
                           "(documents), copied unchanged; they are not "
                           "pseudonymised",
        "order": "in the order given, a folder's files by name",
    }
    if backup:
        batch.update(backup)
    answer["batch"] = batch
    answer["closing"] = ("If your app asks whether to allow the import, "
                         "allow it once, after reading this preview.")
    return answer


def not_read_note(count: int, ready: bool, held_or_refused: bool) -> str:
    """What the preview says of the files its time left unread: why,
    and how to go on with them."""
    files = f"{count} file{'s' if count != 1 else ''}"
    note = (f"{files} {'were' if count != 1 else 'was'} not read in this "
            f"call: Exegete reads for about {PREVIEW_SECONDS} seconds a "
            f"call, since an app can stop a call that runs longer. ")
    if ready:
        note += ("Import the files above with the token if the researcher "
                 "agrees; then call again with the same paths, without a "
                 "token, for a preview of the rest (files already in the "
                 "project are skipped).")
    else:
        note += ("Call again with the same paths, without a token, for a "
                 "preview of the rest.")
    if held_or_refused:
        note += (" The files held back or refused above are read again "
                 "each time they are named: leaving them out (or moving "
                 "them out of the folder) saves that time.")
    return note


def not_imported_note(count: int) -> str:
    """What the import says of the files left for the next call."""
    files = f"{count} file{'s' if count != 1 else ''}"
    return (f"{files} of this batch {'were' if count != 1 else 'was'} not "
            f"imported this time: Exegete works for about "
            f"{IMPORT_SECONDS} seconds a call, since an app can stop a "
            f"call that runs longer, and leaves the rest for the next. "
            f"Call import_documents again with the same paths, without a "
            f"token, for a preview of them; the files imported now are "
            f"skipped.")


# ---------------------------------------------------------------------------
# The import itself: copies, then rows, in the server's transaction
# ---------------------------------------------------------------------------

class BatchFailed(Exception):
    """The batch cannot be written; nothing it made is left behind. The
    code is one of Exegete's own."""

    def __init__(self, code: str, file: Optional[str] = None):
        super().__init__(code)
        self.code = code
        self.file = file


DOCUMENTS_NOT_A_FOLDER = (
    "The project's folder of originals ('documents') is a link, or not an "
    "ordinary folder, so Exegete copies nothing into it: the copies would "
    "land outside the project, where its backups do not reach. Make it an "
    "ordinary folder inside the project, then ask again.")


BATCH_FAILURES = {
    "changed": "A file changed since the preview (its contents are no "
               "longer those previewed). Ask for a fresh preview; nothing "
               "was imported.",
    "not_copied": "An original could not be copied into the project's "
                   "folder of originals (check the disk's free space and "
                   "permissions); nothing was imported.",
    "name_taken": "A file appeared in the project's folder of originals "
                  "under one of these names since the preview; nothing was "
                  "imported. Ask for a fresh preview.",
    "documents_not_a_folder": DOCUMENTS_NOT_A_FOLDER + " Nothing was "
                              "imported.",
    "differs": "A file read differently at the import than at the preview "
               "(reading it took too long or needed too much memory this "
               "time, say); nothing was imported. Ask for a fresh preview, "
               "or leave that file out.",
}


def documents_folder_problem(project_folder: Path) -> Optional[str]:
    """None when the project's folder of originals is absent (the import
    makes it) or an ordinary folder inside the project, not a link or a
    junction (the reading route's rule); else why not, in words."""
    from . import reading_folder
    from .path_identity import is_inside
    folder = Path(project_folder) / "documents"
    try:
        info = os.lstat(folder)
    except FileNotFoundError:
        return None
    except OSError:
        return DOCUMENTS_NOT_A_FOLDER
    if (not stat.S_ISDIR(info.st_mode) or reading_folder.is_link(folder)
            or not is_inside(folder, Path(project_folder))):
        return DOCUMENTS_NOT_A_FOLDER
    return None


def sweep_temporary_copies(documents: Path) -> int:
    """Remove what an interrupted import left in the folder of originals
    (recognised by Exegete's own prefix): regular files only, and never
    through a folder of originals that is a link."""
    removed = 0
    if documents_folder_problem(documents.parent) is not None:
        return 0
    try:
        entries = list(os.scandir(documents))
    except OSError:
        return 0
    for entry in entries:
        if not entry.name.startswith(TEMP_PREFIX):
            continue
        try:
            if entry.is_file(follow_symlinks=False):
                os.unlink(entry.path)
                removed += 1
        except OSError:
            pass
    return removed


def _carry_mark(source: Path, copy: Path) -> Optional[bool]:
    """The internet-origin mark, carried from the original to its copy
    (origin_mark says how; metadata only)."""
    from . import origin_mark
    try:
        return origin_mark.carry(source, copy)
    except Exception:
        return False


def _write_new_file(path: Path, data: bytes) -> None:
    """A new file, never replacing one, without permission to run."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags, 0o644)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish(temp: Path, final: Path, written: "Written") -> None:
    """Give a complete copy its final name, never replacing a file. The
    final name is recorded the moment it exists, so a failure after it
    (removing the temporary name, say) still takes it back."""
    if os.name == "nt":
        os.rename(temp, final)          # refuses an existing name
        written.moved(temp, final)
        return
    try:
        os.link(temp, final)            # refuses an existing name
    except FileExistsError:
        raise
    except OSError:
        # A disk without hard links (exFAT, some shares): the name was
        # checked free under the lock, so a rename after one more look.
        if os.path.lexists(final):
            raise FileExistsError(str(final)) from None
        os.rename(temp, final)
        written.moved(temp, final)
        return
    written.finals.append(final)
    os.unlink(temp)
    written.temps.remove(temp)


@dataclass
class Written:
    """What a batch put on the disk, so a failure can take it all back."""
    temps: List[Path] = field(default_factory=list)
    finals: List[Path] = field(default_factory=list)
    marks_lost: int = 0

    def moved(self, temp: Path, final: Path) -> None:
        self.finals.append(final)
        self.temps.remove(temp)

    def remove_all(self) -> None:
        for path in self.temps + self.finals:
            try:
                os.unlink(path)
            except OSError:
                pass
        self.temps, self.finals = [], []


def write_batch(insert_row: Callable[..., Dict[str, Any]], result: Survey,
                ctx: Context, owner: str, written: Written,
                now: Optional[Callable[[], float]] = None) -> List[Item]:
    """Copy each file's original into the folder of originals under a
    temporary name, check the copy, read its text from the copy's bytes,
    and write its row through `insert_row`; then give the copies their
    names. Raises BatchFailed; the caller rolls back and calls
    `written.remove_all()`.

    The import works for `ctx.import_seconds` from the call's start: the
    first file always has its whole time (IMPORT_FILE_SECONDS); after
    it, a file there is no time left for, or whose reading the time left
    cut short, stops the call there, and it and the files after it are
    left for the next call (status "later"): the files before it are
    imported, as the answer says."""
    documents = ctx.project_folder / "documents"
    if documents_folder_problem(ctx.project_folder) is not None:
        raise BatchFailed("documents_not_a_folder")
    try:
        documents.mkdir(exist_ok=True)
    except OSError:
        raise BatchFailed("not_copied") from None
    if documents_folder_problem(ctx.project_folder) is not None:
        raise BatchFailed("documents_not_a_folder")
    now = now or clock
    started = ctx.call_started if ctx.call_started is not None else now()
    taken: List[Item] = []
    stopped = False
    for item in result.items:
        if item.status != "ready":
            continue
        timeout = None if stopped else _time_for(
            IMPORT_FILE_SECONDS, ctx.import_seconds, started, not taken, now)
        if timeout is None:
            stopped = True
            item.status, item.code = "later", NOT_IMPORTED_THIS_TIME
            continue
        try:
            data, _size = read_bytes(item.path, SIZE_LIMITS[item.kind])
        except _ReadRefusal:
            raise BatchFailed("changed") from None
        if data is None or digest_of(data) != item.digest:
            raise BatchFailed("changed")
        temp = documents / f"{TEMP_PREFIX}{secrets.token_hex(4)}-{item.name}"
        try:
            _write_new_file(temp, data)
        except OSError:
            raise BatchFailed("not_copied") from None
        written.temps.append(temp)
        if _carry_mark(item.path, temp) is False:
            written.marks_lost += 1
        try:
            copy, _size = read_bytes(temp, SIZE_LIMITS[item.kind])
        except _ReadRefusal:
            raise BatchFailed("not_copied") from None
        if copy is None or digest_of(copy) != item.digest:
            raise BatchFailed("not_copied")
        _read_one(item, copy, ctx, timeout, IMPORT_FILE_SECONDS,
                  NOT_IMPORTED_THIS_TIME)
        if item.status == "later":
            # Its reading was cut short by the call's time: neither it
            # nor any file after it goes in this time.
            written.temps.remove(temp)
            try:
                temp.unlink()
            except OSError:
                pass
            stopped = True
            continue
        if item.status != "ready":
            # The preview read this file as ready, and the researcher
            # approved the batch with it in: a file that now reads
            # otherwise (it ran out of time or memory, say) stops the
            # whole batch, which goes in together or not at all. Files
            # the preview held back or refused were never taken up here.
            raise BatchFailed("differs", file=item_label(item))
        row = insert_row(name=item.name, fulltext=item.text,
                         mediapath="/docs/" + item.name, memo=item.memo,
                         owner=owner)
        item.numbers["file_id"] = row["id"]
        item.numbers["temp"] = str(temp)
        taken.append(item)
    for item in taken:
        temp = Path(item.numbers.pop("temp"))
        final = documents / item.name
        try:
            _publish(temp, final, written)
        except FileExistsError:
            raise BatchFailed("name_taken") from None
        except OSError:
            raise BatchFailed("not_copied") from None
    return taken
