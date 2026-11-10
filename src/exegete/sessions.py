# SPDX-License-Identifier: LGPL-3.0-or-later
"""Session management for AI coding suggestions with disk persistence.

From 0.15.4 a new session is kept inside its project, in the project's
`Exegete coding sessions` folder (private_files), and goes wherever the
project goes; a file kept there records no project path, its place
being its project. Sessions made before 0.15.4 stay in the state
folder's `sessions`, tied to their project by the path they record, and
nothing moves; so does a session whose project's folder could not hold
it, with the reason.
"""

import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Dict, NamedTuple, Optional, Any, Tuple

from . import private_files
from .database import error_label

logger = logging.getLogger(__name__)

# Where a session's file is kept (v0.15.4), as the session tools say it
KEPT_IN_PROJECT = "project"
KEPT_ON_THIS_COMPUTER = "this computer"


def _now() -> datetime:
    """The time now, for the sessions' ages (one place, so that a test
    can fix the clock)."""
    return datetime.now()


def days_back_to_year_one(now: Optional[datetime] = None) -> int:
    """The most days a session list can count back (v0.15.4): the whole
    days from the start of the year 1, the earliest date Python's dates
    hold, to now. One more counts back past it, which Python cannot do
    (739,929 on 10 November 2026, one more each day)."""
    return ((now or _now()) - datetime.min).days


class SessionFileError(ValueError):
    """A session's file that could not be read, saved or removed in the
    project's sessions folder, or a start refused, with the reason in
    plain words: no path, nothing the file holds. `code` says which. A
    ValueError, so that a tool answers its message (v0.15.4)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# How a suggested code reads the passage (owner rulings 21 and 25, v0.14):
# a category, never a number, and the researcher's to change at review.
# Nothing sorts, filters or totals by it. `explicit`: the passage states
# what the code names; `interpretive`: the code rests on what the passage
# implies rather than on what it says (the reason then names the words it
# rests on). A suggestion recorded before v0.14 carried a 0-1
# "confidence" instead; it loads with no label (None), and the number is
# not kept. A session written while the label was called `support` loads
# its value as the reading.
READING_LABELS = {
    "explicit": "the passage states what the code names",
    "interpretive": ("the code rests on what the passage implies rather "
                     "than on what it says"),
}


def reading_label(value: Any) -> Optional[str]:
    """The label a value names ('explicit' or 'interpretive'), or None.

    Only a string can name one: a list, a number or a boolean is no label
    (and a list cannot even be looked up in a dict)."""
    return value if isinstance(value, str) and value in READING_LABELS else None


def reading_in_words(reading: Optional[str]) -> Optional[str]:
    """'explicit (the passage states what the code names)', or None for
    no label."""
    label = reading_label(reading)
    if label is None:
        return None
    return f"{label} ({READING_LABELS[label]})"


def guids_in_more_than_one(*lists: Optional[List[Any]]) -> List[Any]:
    """GUIDs that appear in more than one of the decision lists, in order.

    A GUID sent to approve and to reject used to be counted as both and
    end rejected; the decision tools refuse such a call instead."""
    seen: Dict[Any, set] = {}
    for index, values in enumerate(lists):
        for value in (values or []):
            key = value if isinstance(value, (str, int)) else repr(value)
            seen.setdefault(key, set()).add(index)
    return [key for key, where in seen.items() if len(where) > 1]


# What the server writes as a proposal's merged_into: a GUID, uuid4's own
# shape. Anything else in a session file (crafted or damaged) is not
# echoed (fix round 1); matched whole, so no trailing newline gets
# through (fix round 2)
_GUID_SHAPE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}")


def unique_in_order(values: Optional[List[Any]]) -> List[Any]:
    """Each value once, first mention first: a GUID named twice in one
    list is one decision, and is counted once."""
    out: List[Any] = []
    for value in (values or []):
        if value not in out:
            out.append(value)
    return out


def memo_with_reading(reasoning: str, reading: Optional[str]) -> str:
    """The text an applied suggestion carries in its coding memo, and in a
    REFI-QDA export's selection description: the reading in words
    FIRST, then the reason. First, because a reason holding QualCoder's
    '#####' private marker keeps only what comes before it, and the label
    must survive that. No label (a pre-v0.14 suggestion, or a coding read
    back from the project for an export): the text exactly as given, not
    trimmed, since a project export carries every memo as QualCoder
    stores it. Never a number (owner ruling 21)."""
    label = reading_in_words(reading)
    if label is None:
        return reasoning or ""
    parts = [f"Reading: {label}", (reasoning or "").strip()]
    return "\n\n".join(part for part in parts if part)


class CodingSuggestion:
    """Data class for AI-suggested coding with conversational review support."""

    def __init__(
        self,
        file_id: int,
        file_name: str,
        code_id: int,
        code_name: str,
        start_pos: int,
        end_pos: int,
        segment_text: str,
        reasoning: str = "",
        reading: Optional[str] = None,
        status: str = "pending",
        guid: Optional[str] = None,
        span_alternatives: Optional[List[Dict[str, Any]]] = None,
        adjusted: bool = False,
        applied_ctid: Optional[int] = None,
        reading_cleared: bool = False,
    ):
        self.file_id = file_id
        self.file_name = file_name
        self.code_id = code_id
        self.code_name = code_name
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.segment_text = segment_text
        self.reasoning = reasoning  # Why this segment was coded
        # 'explicit' | 'interpretive' | None (recorded before v0.14, or a
        # row read back from the project, which carries no label)
        self.reading = reading_label(reading)
        # True when edit_suggestion moved the suggestion to another code
        # without a new label: the old one was given for the old code, so
        # it is cleared rather than carried (fix round 1)
        self.reading_cleared = bool(reading_cleared) and self.reading is None
        # 'pending', 'approved', 'rejected', 'applied', or 'removed' (it
        # was applied, then its coding was deleted with delete_coding)
        self.status = status
        # No surrounding text is kept (owner ruling 25, question 9): the
        # review reads it from the file when it is shown, and a stored
        # context_before/context_after from an earlier file is neither
        # shown nor written back
        self.guid = guid or str(uuid.uuid4())
        # Server-computed ready-made span adjustments (shorter/longer).
        # Presentational only: use_alternative recomputes from the current
        # fulltext at edit time. [] for pre-v0.8 sessions (zero migration).
        # A span's text is not kept (owner ruling 25, question 9): a
        # "preview" an earlier release stored is dropped here, so it is
        # never shown and is gone at the next save
        self.span_alternatives = [
            {k: v for k, v in alt.items() if k != "preview"}
            if isinstance(alt, dict) else alt
            for alt in (span_alternatives or [])]
        # True once the researcher edited this suggestion (span or code) —
        # review stops offering alternatives on decided-and-adjusted spans
        self.adjusted = bool(adjusted)
        # The ctid apply_codings wrote (or found) for this suggestion, so
        # delete_coding can tell the session which suggestion it undid.
        # None before v0.14 and until the suggestion is applied.
        self.applied_ctid = (applied_ctid if isinstance(applied_ctid, int)
                             and not isinstance(applied_ctid, bool) else None)

        # For backwards compatibility with old ai_memo field
        self.ai_memo = reasoning

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialisation."""
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "code_id": self.code_id,
            "code_name": self.code_name,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "segment_text": self.segment_text,
            "reasoning": self.reasoning,
            "reading": self.reading,
            "status": self.status,
            "guid": self.guid,
            "span_alternatives": self.span_alternatives,
            "adjusted": self.adjusted,
            "applied_ctid": self.applied_ctid,
            "reading_cleared": self.reading_cleared,
        }

    _REQUIRED_FIELDS = {
        "file_id", "file_name", "code_id", "code_name",
        "start_pos", "end_pos", "segment_text"
    }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodingSuggestion':
        """Create from dictionary.

        Raises:
            ValueError: If required fields are missing
            TypeError: If data is not a dictionary
        """
        if not isinstance(data, dict):
            raise TypeError("CodingSuggestion data must be a dictionary")

        missing = cls._REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Handle both old (ai_memo) and new (reasoning) formats
        reasoning = data.get("reasoning") or data.get("ai_memo", "")

        return cls(
            file_id=data["file_id"],
            file_name=data["file_name"],
            code_id=data["code_id"],
            code_name=data["code_name"],
            start_pos=data["start_pos"],
            end_pos=data["end_pos"],
            segment_text=data["segment_text"],
            reasoning=reasoning,
            # A pre-v0.14 file carries "confidence" (a number) and no
            # label: it loads with none, and the number is dropped. A file
            # written while the label was called "support" loads it as
            # the reading
            reading=(data.get("reading") if "reading" in data
                     else data.get("support")),
            status=data.get("status", "pending"),
            guid=data.get("guid"),
            span_alternatives=data.get("span_alternatives"),
            adjusted=data.get("adjusted", False),
            applied_ctid=data.get("applied_ctid"),
            reading_cleared=(data.get("reading_cleared")
                             or data.get("support_cleared", False)),
        )


class ProposedCode:
    """A brand-new code the AI proposes from the data (inductive coding).

    Distinct from a CodingSuggestion: a proposal carries a code definition
    (name/colour/category/memo) plus evidence spans, and only becomes a
    real code when the user approves it and create_proposed_codes runs.
    Status lifecycle: pending -> approved/rejected -> created; a proposal
    merged into another is "merged", which is final (v0.14): it can never
    be approved or created, so its evidence is never written twice. Any
    change to an approved proposal returns it to pending.
    """

    def __init__(
        self,
        name: str,
        memo: str = "",
        rationale: str = "",
        color: Optional[str] = None,
        category: Optional[str] = None,
        status: str = "pending",
        example_segments: Optional[List[Dict[str, Any]]] = None,
        collides_with: Optional[str] = None,
        created_code_id: Optional[int] = None,
        guid: Optional[str] = None,
        merged_into: Optional[str] = None,
    ):
        self.name = name
        self.memo = memo                    # the code definition
        self.rationale = rationale          # why this code emerges
        self.color = color                  # None -> palette pick at creation
        self.category = category            # existing category NAME or None
        self.status = status        # pending/approved/rejected/created/merged
        self.example_segments = example_segments or []
        self.collides_with = collides_with  # existing code name, if any
        self.created_code_id = created_code_id
        self.guid = guid or str(uuid.uuid4())
        # the target's GUID, once merged; only that shape is kept, since it
        # is echoed into the conversation
        self.merged_into = (merged_into if isinstance(merged_into, str)
                            and _GUID_SHAPE.fullmatch(merged_into) else None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "guid": self.guid,
            "name": self.name,
            "memo": self.memo,
            "rationale": self.rationale,
            "color": self.color,
            "category": self.category,
            "status": self.status,
            "example_segments": self.example_segments,
            "collides_with": self.collides_with,
            "created_code_id": self.created_code_id,
            "merged_into": self.merged_into,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProposedCode':
        if not isinstance(data, dict):
            raise TypeError("ProposedCode data must be a dictionary")
        if "name" not in data:
            raise ValueError("Missing required field: name")
        return cls(
            name=data["name"],
            memo=data.get("memo", ""),
            rationale=data.get("rationale", ""),
            color=data.get("color"),
            category=data.get("category"),
            status=data.get("status", "pending"),
            # Shorter and longer spans are no longer stored on proposal
            # passages (owner ruling 25, question 8): a session file
            # written earlier loses them when it is next saved
            example_segments=[
                {k: v for k, v in seg.items() if k != "span_alternatives"}
                if isinstance(seg, dict) else seg
                for seg in (data.get("example_segments") or [])],
            collides_with=data.get("collides_with"),
            created_code_id=data.get("created_code_id"),
            guid=data.get("guid"),
            merged_into=data.get("merged_into"),
        )


# `outside_scope` given no code date (v0.15.4): the number alone is checked
_DATE_NOT_GIVEN = object()


class AICodingSession:
    """Manages a session of AI coding suggestions."""

    def __init__(
        self,
        project_path: str,
        session_id: Optional[str] = None,
        description: str = "",
        file_ids: Optional[List[int]] = None,
        code_names: Optional[List[str]] = None,
        instruction: str = "",
        ai_coder_name_at_record: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id or str(uuid.uuid4())
        # What record_suggestions may record in this session (v0.14, the
        # claims audit's item 10): {"file_ids": [...], "code_ids": [...] or
        # None for every code}. None for a session made before v0.14 (or
        # built directly), whose file_ids and code_names were only ever a
        # note: those sessions keep that behaviour. From 0.15.4 a scope
        # limited to named codes also keeps each code's date beside its
        # number, "code_dates" ({"<number>": "<date>"}): SQLite gives a
        # deleted code's number to the next code made, and the date, kept
        # to the second, tells the two apart unless the one was deleted
        # and the other made within the same second. A session without
        # it is checked by number alone.
        self.scope = self._clean_scope(scope)
        # A scope that is there but cannot be read (a damaged or hand-made
        # file) fails closed: nothing is recorded into the session, rather
        # than every limit being lifted as for a session with none (fix
        # round 1). The raw value is written back unchanged.
        self.scope_unreadable = scope is not None and self.scope is None
        self._raw_scope = scope if self.scope_unreadable else None
        # The project's AI coder name AT THE MOMENT the session was
        # created (v0.12, D7 section 7). Suggestions recorded under one
        # name and applied after the researcher changed it are still
        # written under the CURRENT name, because a name change never
        # re-attributes anything; the snapshot exists so the apply can
        # SAY so. Absent in 0.11 session files, which is why it is
        # optional here and read with a default below.
        self.ai_coder_name_at_record = ai_coder_name_at_record
        # Ensure project_path is always a string for JSON serialization
        self.project_path = str(project_path) if project_path else ""
        self.description = description
        self.file_ids = file_ids or []
        self.code_names = code_names or []
        self.instruction = instruction
        self.suggestions: List[CodingSuggestion] = []
        self.proposed_codes: List[ProposedCode] = []
        # Span-affordance bookkeeping (tester-feedback amendment): counts
        # drive the one-time shortcut hint (first manual span edit) and the
        # calibration-escalation hint (3 same-direction alternative picks)
        self.span_edit_stats: Dict[str, int] = {
            "manual_edits": 0, "shorter_picks": 0, "longer_picks": 0}
        self.created_at = datetime.now().isoformat()
        self.last_modified = self.created_at
        # Where the session's file is kept (v0.15.4), never written into
        # it: KEPT_IN_PROJECT, in `kept_folder`'s sessions folder, or
        # KEPT_ON_THIS_COMPUTER, in the state folder. None until it is
        # first saved or read; a session is saved where it was read.
        self.kept_in: Optional[str] = None
        self.kept_folder: Optional[Path] = None
        # Why a new session is kept on this computer although its project
        # is open: the reason its project's folder could not hold it
        self.kept_reason: Optional[str] = None

    @staticmethod
    def _clean_scope(scope: Any) -> Optional[Dict[str, Any]]:
        """A scope read from disk, or None if it is not a well-formed one."""
        def ids(value):
            if not isinstance(value, list):
                return None
            if not all(isinstance(v, int) and not isinstance(v, bool)
                       for v in value):
                return None
            return list(value)
        if not isinstance(scope, dict):
            return None
        file_ids = ids(scope.get("file_ids"))
        if file_ids is None:
            return None
        code_ids = scope.get("code_ids")
        if code_ids is not None:
            code_ids = ids(code_ids)
            if code_ids is None:
                return None
        cleaned = {"file_ids": file_ids, "code_ids": code_ids}
        # The codes' dates (v0.15.4): only a text for a number the scope
        # holds is kept; anything else is read past, and a session whose
        # dates cannot be read at all is checked by number, as before
        dates = scope.get("code_dates")
        if code_ids is not None and isinstance(dates, dict):
            numbers = {str(cid) for cid in code_ids}
            cleaned["code_dates"] = {
                key: value for key, value in dates.items()
                if isinstance(key, str) and key in numbers
                and isinstance(value, str)}
        return cleaned

    def _recorded_date(self, code_id: int) -> Optional[str]:
        """The date the scope recorded for a code's number, or None."""
        dates = (self.scope or {}).get("code_dates")
        return dates.get(str(code_id)) if isinstance(dates, dict) else None

    def outside_scope(self, file_id: int, code_id: Optional[int] = None,
                      code_date: Any = _DATE_NOT_GIVEN) -> Optional[str]:
        """Which part of the scope a file or code falls outside, or None.

        'file' or 'code'; 'unreadable' when the session's scope is there but
        cannot be read; None when the session has no scope (made before
        v0.14) or both are inside it. code_id None checks the file only.
        `code_date` (v0.15.4) is the code's date as the codebook holds it
        now: a code whose number the scope holds under another date is
        another code, given the number of one deleted since, and falls
        outside ('code')."""
        if self.scope_unreadable:
            return "unreadable"
        if self.scope is None:
            return None
        if file_id not in self.scope["file_ids"]:
            return "file"
        codes = self.scope["code_ids"]
        if code_id is not None and codes is not None:
            if code_id not in codes:
                return "code"
            recorded = self._recorded_date(code_id)
            if (code_date is not _DATE_NOT_GIVEN and recorded is not None
                    and code_date != recorded):
                return "code"
        return None

    def scope_recorded(self, code_id: int, code_date: Any) -> bool:
        """Whether this session's scope names the code of that number and
        date (v0.15.4): its number is there with that date, or with none
        recorded. Undo takes a removed code out of a scope only where it
        did, so undoing a later code given a deleted code's number leaves
        the session's own code in its scope."""
        if self.scope is None or self.scope.get("code_ids") is None:
            return False
        if code_id not in self.scope["code_ids"]:
            return False
        recorded = self._recorded_date(code_id)
        return recorded is None or recorded == code_date

    def add_codes_to_scope(self, codes: Dict[int, Any]) -> None:
        """Codes created from this session's approved proposals join a
        session limited to named codes, so the loop can apply them: each
        number added where it is missing, and its date set (v0.15.4),
        replacing the one recorded where the number is already there (the
        session's own code deleted, and its number given to the code its
        proposal made). `codes`: each new code's number and date, as its
        write read the row back."""
        if not codes or self.scope is None or self.scope["code_ids"] is None:
            return
        dates = self.scope.setdefault("code_dates", {})
        for cid, date in codes.items():
            if cid not in self.scope["code_ids"]:
                self.scope["code_ids"].append(cid)
            if isinstance(date, str):
                dates[str(cid)] = date
            else:
                dates.pop(str(cid), None)

    def add_suggestion(self, suggestion: CodingSuggestion):
        """Add a coding suggestion to the session."""
        self.suggestions.append(suggestion)
        self.last_modified = datetime.now().isoformat()

    def add_proposal(self, proposal: 'ProposedCode'):
        """Add a proposed code to the session."""
        self.proposed_codes.append(proposal)
        self.last_modified = datetime.now().isoformat()

    def get_proposal_by_guid(self, guid: str) -> Optional['ProposedCode']:
        for p in self.proposed_codes:
            if p.guid == guid:
                return p
        return None

    def proposal_statistics(self) -> Dict[str, int]:
        counts = {"total_proposals": len(self.proposed_codes),
                  "pending": 0, "approved": 0, "rejected": 0, "created": 0,
                  "merged": 0}
        for p in self.proposed_codes:
            if p.status in counts:
                counts[p.status] += 1
        return counts

    def update_proposals_by_guid(
        self,
        approve: Optional[List[str]] = None,
        reject: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Approve/reject proposals. CREATED proposals are immutable
        (they are already in the codebook) and MERGED ones are final
        (v0.14): both are skipped and counted, mirroring the
        applied-immutable rule for suggestions (QA2-2). GUIDs that name
        no proposal in this session come back in `not_found`. Each GUID is
        counted once, and `approved` and `rejected` count only proposals
        whose status moved; one that already had that status is counted
        in `unchanged` (fix round 1: the counts are what the researcher
        checks against what they said). The caller refuses a GUID given
        in both lists before calling."""
        counts = {"approved": 0, "rejected": 0, "unchanged": 0,
                  "skipped_created": 0, "skipped_merged": 0, "changed": 0}
        not_found: List[Any] = []
        for guids, status in ((approve, "approved"), (reject, "rejected")):
            for guid in unique_in_order(guids):
                p = self.get_proposal_by_guid(guid)
                if p is None:
                    not_found.append(guid)
                    continue
                if p.status in ("created", "merged"):
                    counts[f"skipped_{p.status}"] += 1
                    continue
                if p.status == status:
                    counts["unchanged"] += 1
                    continue
                p.status = status
                counts[status] += 1
                counts["changed"] += 1
        if counts["changed"]:
            self.last_modified = datetime.now().isoformat()
        return {**counts, "not_found": not_found}

    def get_suggestions_by_file(self, file_id: int) -> List[CodingSuggestion]:
        """Get all suggestions for a specific file."""
        return [s for s in self.suggestions if s.file_id == file_id]

    def get_suggestions_by_code(self, code_id: int) -> List[CodingSuggestion]:
        """Get all suggestions for a specific code."""
        return [s for s in self.suggestions if s.code_id == code_id]

    def filter_by_status(self, status: str) -> List[CodingSuggestion]:
        """Get suggestions by status (pending/approved/rejected)."""
        return [s for s in self.suggestions if s.status == status]

    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        total = len(self.suggestions)
        approved = len([s for s in self.suggestions if s.status == "approved"])
        rejected = len([s for s in self.suggestions if s.status == "rejected"])
        pending = len([s for s in self.suggestions if s.status == "pending"])
        applied = len([s for s in self.suggestions if s.status == "applied"])
        removed = len([s for s in self.suggestions if s.status == "removed"])

        # By file
        by_file = {}
        for s in self.suggestions:
            if s.file_name not in by_file:
                by_file[s.file_name] = 0
            by_file[s.file_name] += 1

        # By code
        by_code = {}
        for s in self.suggestions:
            if s.code_name not in by_code:
                by_code[s.code_name] = 0
            by_code[s.code_name] += 1

        return {
            "total_suggestions": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "applied": applied,
            "removed": removed,
            "by_file": by_file,
            "by_code": by_code
        }

    def has_duplicate(self, file_id: int, code_id: int,
                      start_pos: int, end_pos: int) -> bool:
        """Check whether an equivalent suggestion is already in the session.

        A suggestion whose coding was deleted (status "removed") does not
        count: the same passage can be recorded again after the undo."""
        for s in self.suggestions:
            if s.status == "removed":
                continue
            if (s.file_id == file_id and s.code_id == code_id
                    and s.start_pos == start_pos and s.end_pos == end_pos):
                return True
        return False

    def remove_pending_suggestions(self) -> int:
        """Remove all pending suggestions (used by record_suggestions replace).

        Approved, rejected, and applied suggestions are never removed.

        Returns:
            Number of suggestions removed
        """
        before = len(self.suggestions)
        self.suggestions = [s for s in self.suggestions if s.status != "pending"]
        removed = before - len(self.suggestions)
        if removed:
            self.last_modified = datetime.now().isoformat()
        return removed

    def mark_applied(self, guids: List[str],
                     ctids: Optional[Dict[str, int]] = None) -> int:
        """Mark suggestions as applied (written to the database).

        Args:
            guids: GUIDs of the suggestions that were written
            ctids: the coding each one became, by GUID, kept so that
                   delete_coding can find the suggestion it undoes

        Returns:
            Number of suggestions marked
        """
        count = 0
        for guid in guids:
            sugg = self.get_suggestion_by_guid(guid)
            if sugg is not None:
                sugg.status = "applied"
                if ctids and guid in ctids:
                    sugg.applied_ctid = ctids[guid]
                count += 1
        if count:
            self.last_modified = datetime.now().isoformat()
        return count

    def get_suggestion_by_guid(self, guid: str) -> Optional[CodingSuggestion]:
        """Get a suggestion by its GUID."""
        for s in self.suggestions:
            if s.guid == guid:
                return s
        return None

    def update_suggestion_status(self, index: int, status: str) -> bool:
        """Update the status of a suggestion by index.

        Args:
            index: Index of the suggestion in the list
            status: New status ('approved' or 'rejected')

        Returns:
            True if updated, False if index out of range
        """
        if 0 <= index < len(self.suggestions):
            self.suggestions[index].status = status
            self.last_modified = datetime.now().isoformat()
            return True
        return False

    def update_suggestions_by_guid(
        self,
        approve: Optional[List[str]] = None,
        reject: Optional[List[str]] = None,
        reopen: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Approve, reject or reopen suggestions by GUID.

        Suggestions already APPLIED to the database are immutable here:
        re-approving one would undo the double-apply bookkeeping and make
        the next apply_codings fail wholesale on the duplicate constraint
        (QA2-2). They are skipped and counted. `reopen` returns an
        approved, rejected or removed suggestion to pending, so it can be
        edited and decided again (v0.14; before it, nothing could, and
        edit_suggestion's own advice went in a circle). GUIDs that name no
        suggestion in this session come back in `not_found`. Each GUID is
        counted once, and approved, rejected and reopened count only the
        suggestions whose status moved; one that already had that status
        is counted in `unchanged` (fix round 1: the researcher checks the
        approved number against what they said yes to). The caller
        refuses a GUID given in more than one list before calling.

        Returns:
            Counts of approved, rejected, reopened, unchanged,
            skipped_applied and changed, and the not_found list
        """
        counts = {"approved": 0, "rejected": 0, "reopened": 0,
                  "unchanged": 0, "skipped_applied": 0, "changed": 0}
        not_found: List[Any] = []
        for guids, status, key in ((approve, "approved", "approved"),
                                   (reject, "rejected", "rejected"),
                                   (reopen, "pending", "reopened")):
            for guid in unique_in_order(guids):
                sugg = self.get_suggestion_by_guid(guid)
                if sugg is None:
                    not_found.append(guid)
                    continue
                if sugg.status == "applied":
                    counts["skipped_applied"] += 1
                    continue
                if sugg.status == status:
                    counts["unchanged"] += 1
                    continue
                sugg.status = status
                counts[key] += 1
                counts["changed"] += 1
        if counts["changed"]:
            self.last_modified = datetime.now().isoformat()
        return {**counts, "not_found": not_found}

    def mark_removed(self, file_id: int, code_id: int, start_pos: int,
                     end_pos: int, ctid: int, owner_is_ai: bool) -> List[str]:
        """The applied suggestions a deleted coding undid: marked removed.

        A suggestion matches when its file, code and span are the deleted
        row's, the deleted row was written under one of the project's AI
        coder names, and, where apply_codings recorded the ctid it wrote
        (v0.14 on), that ctid is the deleted one. The owner is checked in
        every case: SQLite hands the highest coding id out again once its
        row is gone, so a person's coding of the same span can carry the
        id an AI coding had (fix round 1). Deleting a person's coding
        never touches a suggestion.

        Returns:
            The GUIDs marked
        """
        marked = []
        for sugg in self.suggestions:
            if (sugg.status != "applied" or sugg.file_id != file_id
                    or sugg.code_id != code_id
                    or sugg.start_pos != start_pos
                    or sugg.end_pos != end_pos):
                continue
            if not owner_is_ai:
                continue
            if sugg.applied_ctid is not None and sugg.applied_ctid != ctid:
                continue
            sugg.status = "removed"
            marked.append(sugg.guid)
        if marked:
            self.last_modified = datetime.now().isoformat()
        return marked

    def to_dict(self) -> Dict[str, Any]:
        """Export session as dictionary for JSON export."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "project_path": self.project_path,
            "description": self.description,
            "file_ids": self.file_ids,
            "code_names": self.code_names,
            "instruction": self.instruction,
            "scope": self._raw_scope if self.scope_unreadable else self.scope,
            "ai_coder_name_at_record": self.ai_coder_name_at_record,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "proposed_codes": [p.to_dict() for p in self.proposed_codes],
            "span_edit_stats": self.span_edit_stats,
            "statistics": self.get_statistics(),
            "proposal_statistics": self.proposal_statistics()
        }

    # The fields a session file in the state folder must hold; a file kept
    # in a project holds no project_path (v0.15.4)
    _REQUIRED_FIELDS = {
        "project_path", "session_id", "created_at", "last_modified"
    }

    @classmethod
    def from_dict(cls, data: Dict[str, Any],
                  project_path: Optional[str] = None) -> 'AICodingSession':
        """Create session from dictionary.

        `project_path` (v0.15.4): for a file kept in a project's sessions
        folder, the database of the project it was read from, which takes
        the place of any path the file holds; the file need not hold one.
        Without it, the file's own `project_path` is required, as in the
        state folder.

        Raises:
            ValueError: If required fields are missing
            TypeError: If data is not a dictionary
        """
        if not isinstance(data, dict):
            raise TypeError("AICodingSession data must be a dictionary")

        required = (cls._REQUIRED_FIELDS if project_path is None
                    else cls._REQUIRED_FIELDS - {"project_path"})
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Missing required session fields: {missing}")

        session = cls(
            project_path=(data["project_path"] if project_path is None
                          else project_path),
            session_id=data["session_id"],
            description=data.get("description", ""),
            file_ids=data.get("file_ids", []),
            code_names=data.get("code_names", []),
            instruction=data.get("instruction", ""),
            # A pre-v0.14 file's "min_confidence" is read past: it never
            # filtered anything, and the score it referred to is gone
            # Absent in 0.11 files: no snapshot, so no warning to give
            ai_coder_name_at_record=data.get("ai_coder_name_at_record"),
            # Absent before v0.14: no scope, so nothing is refused
            scope=data.get("scope")
        )
        session.created_at = data["created_at"]
        session.last_modified = data["last_modified"]
        # Absent in pre-v0.8 sessions -> fresh counters (zero migration)
        stats = data.get("span_edit_stats")
        if isinstance(stats, dict):
            session.span_edit_stats = {
                "manual_edits": int(stats.get("manual_edits", 0)),
                "shorter_picks": int(stats.get("shorter_picks", 0)),
                "longer_picks": int(stats.get("longer_picks", 0)),
            }

        # Load suggestions
        for s_data in data.get("suggestions", []):
            suggestion = CodingSuggestion.from_dict(s_data)
            session.suggestions.append(suggestion)

        # Load proposed codes (absent in pre-v0.8 sessions -> [])
        for p_data in data.get("proposed_codes", []):
            session.proposed_codes.append(ProposedCode.from_dict(p_data))

        return session


class SessionsListing(NamedTuple):
    """What a list of sessions found (v0.15.4,
    SessionManager.sessions_listing)."""
    # The sessions, as list_sessions lists them
    sessions: List[Dict[str, Any]]
    # Why the open project's sessions folder could not be read, in the
    # words a lookup gives (a link or a file at its name, a folder its
    # owner alone can read, a path past Windows' limit); None otherwise
    project_folder_refusal: Optional[str]
    # Entries at a session's name in the open project's sessions folder
    # that could not be read, or hold another session's id
    not_read_in_project: int
    # Session files in the state folder that could not be read, or hold
    # another session's id, whichever project they record
    not_read_on_this_computer: int
    # Whether the open project's own folder was read: False when no
    # project is open, or the list was asked for another project
    project_read: bool


class SessionManager:
    """Manage AI coding sessions with disk persistence."""

    # Session IDs must be valid UUID4 strings (hex + hyphens only)
    _SESSION_ID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )

    def __init__(self, storage_dir: Optional[str] = None,
                 project: Optional[Callable[[], Optional[Any]]] = None,
                 no_project: Optional[Callable[[], str]] = None):
        # Constructing a manager must not touch the disk: the server
        # builds one at import time, and `exegete --version` would
        # otherwise create the storage directory before it had even read
        # its own command line (v0.12 fix round 1, F16). The directory is
        # created on the first save; every read path copes with its
        # absence (a glob over a missing directory yields nothing).
        #
        # With no folder given (the server's own manager), the folder is
        # `sessions` in the state folder, chosen at CALL time (v0.14.1):
        # the state folder moves from ~/.qualcoder_mcp to ~/.exegete at
        # the first real start, after this manager was built, and a run
        # whose move could not be made uses the old one for everything.
        self._storage_dir = (None if storage_dir is None
                             else Path(storage_dir).expanduser())
        # `project` (v0.15.4): a function giving the open project's
        # folder, or None when no project is open, called at each lookup
        # and never at construction. A new session of the open project is
        # kept in that project's sessions folder, and a lookup by id reads
        # that folder first. Without it, the state folder alone, as
        # before 0.15.4. `no_project`: the words, with their way on, for
        # a lookup made while no project is open, of a session not on
        # this computer (the server's "No project selected" answer).
        self._project = project
        self._no_project = no_project
        logger.debug("SessionManager storage ready")

    def open_project_folder(self) -> Optional[Path]:
        """The open project's folder, from the function the manager was
        built with; None when there is none or no project is open."""
        if self._project is None:
            return None
        folder = self._project()
        return None if folder is None else Path(folder)

    @staticmethod
    def file_name(session_id: str) -> str:
        """A session's file name, in either place."""
        return f"session_{session_id}.json"

    @property
    def storage_dir(self) -> Path:
        if self._storage_dir is not None:
            return self._storage_dir
        from .preview_tokens import state_home       # no import cycle
        return state_home() / "sessions"

    @storage_dir.setter
    def storage_dir(self, value) -> None:
        self._storage_dir = None if value is None else Path(value)

    def _ensure_storage_dir(self) -> None:
        """Create the storage directory; called before every write."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _validate_session_id(cls, session_id: str) -> str:
        """Validate session ID to prevent path traversal.

        Session IDs must be valid UUID4 format (lowercase hex with hyphens).

        Args:
            session_id: The session ID to validate

        Returns:
            The validated session ID

        Raises:
            ValueError: If session ID is not valid UUID4 format
        """
        if not isinstance(session_id, str):
            raise ValueError("session_id must be a string")
        if not cls._SESSION_ID_PATTERN.match(session_id):
            raise ValueError(
                f"Invalid session ID format: must be UUID4 "
                f"(e.g., '550e8400-e29b-41d4-a716-446655440000')"
            )
        return session_id

    def save_session(self, session: AICodingSession) -> None:
        """Save a session where it is kept (v0.15.4): back where it was
        read; a new one in its project's sessions folder when its project
        is the open one, else in the state folder.

        A new session whose project's folder cannot hold it (a link or a
        file at the folder's name, a read-only project, a path too long
        on Windows) is kept on this computer instead, with the reason in
        `kept_reason`, but only when that attempt left nothing at the
        session's name in the project: otherwise SessionFileError, and
        the session is kept nowhere else, so that no session is in two
        places.

        A save in a project that reports a failure while the file at the
        session's name holds the bytes just written is a save done (a
        network share or a virus scanner can report a replace as failed
        after making it): the session is kept there, and saying it was
        not saved would be untrue.

        Raises:
            ValueError: If session ID is not valid UUID4 format
            SessionFileError: The project's sessions folder refused the
                save, with the reason; the file as it was, or, for a new
                session, a file there that Exegete cannot read back as
                the session
        """
        self._validate_session_id(session.session_id)
        if session.kept_in is None:
            self._save_new(session)
        elif session.kept_in == KEPT_IN_PROJECT:
            self._save_in_project(session, session.kept_folder)
        else:
            self._save_on_this_computer(session)

    def _save_new(self, session: AICodingSession) -> None:
        project = self.open_project_folder()
        if project is None or not self.same_project(
                session.project_path, project / "data.qda"):
            self._save_on_this_computer(session)
            session.kept_in = KEPT_ON_THIS_COMPUTER
            return
        try:
            private_files.ensure_sessions_folder(project)
            self._save_in_project(session, project)
        except (private_files.PrivateFilesError, SessionFileError,
                OSError) as e:
            reason = (str(e) if isinstance(
                e, (private_files.PrivateFilesError, SessionFileError))
                else "Exegete could not write in the project's Exegete "
                     f"coding sessions folder ({error_label(e)}).")
            place = (private_files.sessions_folder(project)
                     / self.file_name(session.session_id))
            if os.path.lexists(place):
                # Only this save can put a file at a new id's name, and
                # one holding the bytes it wrote was taken as the session
                # (_save_in_project): what is there now could not be read
                # back as the session, and may still hold it
                logger.error("A new session could not be kept in its "
                             "project, and something is at its name there")
                raise SessionFileError(
                    "left",
                    "Exegete could not finish saving the new session in "
                    "the project's Exegete coding sessions folder "
                    f"({reason.rstrip('.')}). A file is now at the "
                    "session's name there that Exegete could not read back "
                    "as the session, so the session was not kept on this "
                    "computer as well: if that file holds the session, its "
                    f"id is {session.session_id}, and it is found while "
                    "this project is selected. Asking again starts "
                    "another session."
                ) from None
            logger.warning("A new session is kept on this computer: its "
                           "project's sessions folder could not hold it")
            self._save_on_this_computer(session)
            session.kept_in = KEPT_ON_THIS_COMPUTER
            session.kept_folder = None
            session.kept_reason = reason
            return
        session.kept_in = KEPT_IN_PROJECT
        session.kept_folder = project

    def _save_in_project(self, session: AICodingSession,
                         project: Optional[Path]) -> None:
        """Write a session into a project's sessions folder, without its
        project path (private_files.replace_session: synced, owner-only,
        capped).

        A refusal while the file at the session's name holds the bytes
        just written is a save done, as a network share or a virus
        scanner can report a replace as failed after making it: the
        file is the session, whole, and answering that it was not
        saved, its file as it was, would be untrue."""
        if project is None:
            raise SessionFileError(
                "no_project", "This session's project is not known, so it "
                              "was not saved.")
        data = session.to_dict()
        data.pop("project_path", None)
        raw = json.dumps(data, indent=2).encode("utf-8")
        name = self.file_name(session.session_id)
        try:
            private_files.replace_session(project, name, raw)
        except private_files.PrivateFilesError as e:
            if self._holds(project, name, raw):
                logger.warning(f"Saved session {session.session_id} in its "
                               f"project, though the save reported "
                               f"{error_label(e)}: its file holds it")
                return
            logger.error(f"Failed to save session {session.session_id} in "
                         f"its project: {error_label(e)}")
            raise SessionFileError(e.code, str(e)) from None
        logger.info(f"Saved session {session.session_id}")

    @staticmethod
    def _holds(project: Path, name: str, raw: bytes) -> bool:
        """Whether the project's file at a session's name holds `raw`, read
        through the held folder (private_files.read_session); False when
        it cannot be read, or `raw` is past the cap. Never raises."""
        if len(raw) > private_files.MAX_SESSION:
            return False
        try:
            return private_files.read_session(project, name) == raw
        except (OSError, ValueError, private_files.PrivateFilesError):
            return False

    def _save_on_this_computer(self, session: AICodingSession) -> None:
        """Save session to the state folder as JSON, atomically and
        owner-only.

        The MRU write discipline (server.py _open_mru_tmp), applied here
        because a session file holds the researcher's approvals and a
        torn write would lose them: tempfile.mkstemp opens O_CREAT|O_EXCL
        at mode 0600 under an unpredictable name in the sessions
        directory, so a concurrent host cannot share a temp name and a
        symlink planted at a would-be name is refused rather than written
        through; os.replace is atomic, so a reader sees the old file or
        the new one; a failure unlinks the temp and leaves the previous
        file intact. No fsync: sessions are re-creatable, and the one
        fsync in this server is the AI coder name sidecar, which is not
        (H5, B4.5). A session kept in its project is synced
        (private_files.replace_session), since it travels on whatever
        drive holds the project.
        """
        self._ensure_storage_dir()
        filepath = self.storage_dir / self.file_name(session.session_id)
        tmp = None
        try:
            fd, tmp_name = tempfile.mkstemp(dir=str(self.storage_dir),
                                            prefix=f"{filepath.name}.",
                                            suffix=".tmp")
            tmp = Path(tmp_name)
            # `os.fdopen` either takes the descriptor or raises with it
            # still open and unowned. POSIX hides that: the cleanup can
            # unlink an open file. Windows cannot, and the storage
            # folder keeps the temp for ever (fix round 5).
            try:
                handle = os.fdopen(fd, "w", encoding="utf-8")
            except BaseException:
                os.close(fd)
                raise
            with handle as f:
                json.dump(session.to_dict(), f, indent=2)
            os.replace(str(tmp), str(filepath))
            logger.info(f"Saved session {session.session_id}")
        except Exception as e:
            if tmp is not None:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            logger.error(f"Failed to save session {session.session_id}: {error_label(e)}")
            raise

    def load_session(self, session_id: str) -> AICodingSession:
        """Load session from disk.

        Args:
            session_id: The session ID to load

        Returns:
            The loaded AICodingSession

        Raises:
            ValueError: If session ID is not valid UUID4 format
            FileNotFoundError: If session file doesn't exist
        """
        return self.load_session_and_bytes(session_id)[0]

    def _from_project(self, session_id: str
                      ) -> Tuple[Optional[bytes], Optional[Path],
                                 Optional[SessionFileError]]:
        """The open project's file of an id (v0.15.4): (its bytes, the
        project's folder, None); (None, None, None) when nothing is at
        the id's name there, or the manager keeps no project's sessions;
        (None, None, a refusal) when no project is open or the project's
        sessions folder cannot be read, so that the state folder is read
        and, if it lacks the id too, the refusal given rather than "not
        found", which would be untrue. An entry at the id's name that
        cannot be read (a link, past the cap, unreadable, its path too
        long on Windows) raises SessionFileError: it is that session, and
        is never passed over for the state folder's file of that id."""
        if self._project is None:
            return None, None, None
        project = self.open_project_folder()
        if project is None:
            return None, None, self._no_project_refusal()
        try:
            raw = private_files.read_session(project,
                                             self.file_name(session_id))
        except FileNotFoundError:
            return None, None, None
        except private_files.PrivateFilesError as e:
            if e.about_folder:
                return None, None, self._folder_refusal(e)
            raise SessionFileError(e.code, str(e)) from None
        return raw, project, None

    @staticmethod
    def _folder_refusal(error: private_files.PrivateFilesError
                        ) -> SessionFileError:
        """A session found in neither place while the project's sessions
        folder could not be read: refused with that folder's reason,
        rather than answered as not found."""
        return SessionFileError(
            error.code, "This session is not among those kept on this "
                        f"computer, and the project's could not be read. "
                        f"{error}")

    def _no_project_refusal(self) -> SessionFileError:
        """A session not on this computer, looked for while no project is
        open: it may be kept in a project, found while that project is
        selected."""
        text = ("This session is not among those kept on this computer, "
                "and no project is selected: a session kept in a project "
                "is found while that project is selected.")
        if self._no_project is not None:
            text = f"{text} {self._no_project()}"
        return SessionFileError("no_project", text)

    def load_session_and_bytes(self, session_id: str):
        """Load a session and return it with the file's bytes as read.

        One read serves both, so a caller can later tell whether another
        writer (a second host on the same project) saved the file in the
        meantime (save_session_if_unchanged). A file whose inner id is not
        its name is refused: saving it would write the session its inner
        id names, not the file that was read (fix round 1).

        The open project's sessions folder is read first (v0.15.4): a
        file there is that project's session, its project the open one;
        the state folder is read, as before, only when nothing is at the
        id's name there or the folder cannot be read. The session keeps
        the place it was read from, and is saved there.

        Raises:
            ValueError: If the id is not UUID4, or the file holds another id
            SessionFileError: The project's file at the id's name could
                not be read, with the reason
            FileNotFoundError: If session file doesn't exist
        """
        self._validate_session_id(session_id)
        try:
            raw, project, refusal = self._from_project(session_id)
            if raw is not None:
                data = json.loads(raw.decode("utf-8"))
                session = AICodingSession.from_dict(
                    data, project_path=str(project / "data.qda"))
                kept_in = KEPT_IN_PROJECT
            else:
                filepath = self.storage_dir / self.file_name(session_id)
                if not filepath.exists():
                    if refusal is not None:
                        raise refusal
                    raise FileNotFoundError(
                        f"Session {session_id} not found at {filepath}")
                raw = filepath.read_bytes()
                data = json.loads(raw.decode("utf-8"))
                session = AICodingSession.from_dict(data)
                kept_in, project = KEPT_ON_THIS_COMPUTER, None
            if session.session_id != session_id:
                raise ValueError(
                    f"Session file for {session_id} holds another session's "
                    f"id; it is refused rather than used or written")
            session.kept_in, session.kept_folder = kept_in, project
            logger.info(f"Loaded session {session_id}")
            return session, raw
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {error_label(e)}")
            raise

    def save_session_if_unchanged(self, session: 'AICodingSession',
                                  raw: bytes) -> bool:
        """Save only if the file still holds the bytes it was read with.

        False, and nothing written, when another writer saved it since;
        the caller reads it again and redoes its change on the new copy,
        so a change made meanwhile (a reopen, say) is not undone. The
        window left is the one between this comparison and the replace.
        The file compared is the one at the session's place (v0.15.4)."""
        name = self.file_name(session.session_id)
        try:
            if session.kept_in == KEPT_IN_PROJECT:
                if session.kept_folder is None:
                    return False
                now = private_files.read_session(session.kept_folder, name)
            else:
                now = (self.storage_dir / name).read_bytes()
        except (OSError, private_files.PrivateFilesError):
            return False
        if now != raw:
            return False
        self.save_session(session)
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a session file exists.

        Args:
            session_id: The session ID to check

        Returns:
            True if session file exists, False otherwise.
            Returns False for invalid session ID formats. True also when
            the open project's file at the id's name cannot be read, or
            when the state folder lacks the id while the project's
            sessions folder cannot be read or no project is open
            (v0.15.4): loading it then gives the reason.
        """
        try:
            self._validate_session_id(session_id)
        except ValueError:
            return False
        try:
            raw, _project, refusal = self._from_project(session_id)
        except SessionFileError:
            return True
        if raw is not None:
            return True
        filepath = self.storage_dir / self.file_name(session_id)
        return filepath.exists() or refusal is not None

    def session_file(self, session_id: str) -> Optional[Path]:
        """Where the lookup finds a session's file: the open project's
        sessions folder, else the state folder; None when it is in
        neither. A path for Exegete's own code and its tests, never for
        an answer."""
        try:
            self._validate_session_id(session_id)
        except ValueError:
            return None
        name = self.file_name(session_id)
        project = self.open_project_folder()
        if project is not None:
            place = private_files.sessions_folder(project) / name
            if os.path.lexists(place):
                return place
        place = self.storage_dir / name
        return place if place.exists() else None

    @staticmethod
    def canonical_database_path(project_path: Any) -> Optional[str]:
        """A project's database path in one form, whichever form names it
        (v0.14, the claims audit's item 2), or None for no path.

        A session records its project as the database file
        (`<project>.qda/data.qda`, from `db.db_path`), while
        create_project and select_project given the folder record the
        folder, and a path may carry `~`, a link or a relative part. The
        lists compared those as plain strings, so after create_project
        no session matched the selected project. Both sides are made the
        resolved `data.qda` path here, without opening anything, so a
        moved or deleted project is compared by its name as well.
        """
        if project_path is None or not str(project_path).strip():
            return None
        try:
            path = Path(str(project_path)).expanduser().resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            return str(project_path)
        if path.is_dir() or (path.suffix.lower() == ".qda"
                             and path.name.lower() != "data.qda"
                             and not path.is_file()):
            path = path / "data.qda"
        return str(path)

    @classmethod
    def same_project(cls, first: Any, second: Any) -> bool:
        """Whether two project paths name one project's database (fix
        round 1).

        The canonical strings first, then, when they differ and both
        databases are on disk, the files themselves (device and inode,
        `os.path.samefile`): macOS's disk and Windows' ignore letter case
        and macOS's Unicode form too, and `resolve()` keeps the spelling
        it was given, so `…/study.qda` and `…/Study.qda`, or a name in
        its composed and decomposed forms, are one project with two
        strings. A project no longer on disk is compared by its string.
        """
        a, b = (cls.canonical_database_path(first),
                cls.canonical_database_path(second))
        if a is None or b is None:
            return False
        if a == b:
            return True
        try:
            return os.path.samefile(a, b)
        except (OSError, ValueError):
            return False

    @staticmethod
    def project_name(project_path: Any) -> str:
        """The project's name as the researcher knows it, its folder's,
        not "data" (v0.14)."""
        path = Path(str(project_path))
        if path.name.lower() == "data.qda" and \
                path.parent.suffix.lower() == ".qda":
            path = path.parent
        return path.stem

    def list_sessions(
        self,
        project_path: Optional[str] = None,
        days_old: int = 30
    ) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by project and age.

        The open project's own sessions, kept in its sessions folder, are
        listed beside the state folder's (v0.15.4), each entry with
        `kept_in` (KEPT_IN_PROJECT or KEPT_ON_THIS_COMPUTER); a project's
        own are listed only while it is the open one, and with
        `project_path` only when that path names it. A file holding
        another session's id, a sync service's conflicted copy and a file
        that cannot be read are not listed, and the log counts them,
        naming no file; `sessions_listing` gives those counts, and the
        reason when the project's sessions folder cannot be read, beside
        the list.

        Args:
            project_path: Filter by specific project path (optional)
            days_old: Only show sessions from last N days (default: 30)

        Returns:
            List of session metadata dictionaries. Each entry carries the
            API-facing key ``coding_session_id``; the on-disk files keep
            their own ``session_id`` key, which ``load_session`` continues
            to read.
        """
        return self.sessions_listing(project_path, days_old).sessions

    def sessions_listing(self, project_path: Optional[str] = None,
                         days_old: int = 30) -> SessionsListing:
        """The sessions `list_sessions` lists, with what could not be read
        beside them (v0.15.4), so that an answer never says a project has
        no sessions when its sessions folder, or a session in it, could
        not be read: the folder's refusal in its own words, and the
        entries at a session's name in each place that could not be read
        or hold another session's id, counted, naming none. A sync
        service's conflicted copy is not at a session's name, and is
        neither listed nor counted.

        A `days_old` that counts back past the year 1 raises
        OverflowError, as before: the tool refuses one before it gets
        here (days_back_to_year_one)."""
        sessions = []
        cutoff_date = _now() - timedelta(days=days_old)
        # Compared as databases, whichever form or spelling either side
        # uses (same_project)
        wanted = self.canonical_database_path(project_path)
        skipped = {"another_id": 0, "unreadable": 0}
        # By place, for the answer: the project's entries and the state
        # folder's files that could not be read as their session
        not_read = {KEPT_IN_PROJECT: 0, KEPT_ON_THIS_COMPUTER: 0}
        folder_refusal: Optional[str] = None
        project_read = False

        def listed(data: Dict[str, Any], expected_id: str,
                   project_db: str, kept_in: str) -> None:
            # A copy whose inner id is not its file's name is refused by
            # every tool (load_session), so it is not listed either:
            # listed, it showed the real session's id twice (fix round 2)
            if data.get('session_id') != expected_id:
                skipped["another_id"] += 1
                not_read[kept_in] += 1
                return
            # Filter by project if specified
            if wanted and not self.same_project(project_db, wanted):
                return
            # Filter by age
            last_modified = datetime.fromisoformat(data['last_modified'])
            if last_modified < cutoff_date:
                return
            sessions.append({
                # API-facing key only. The on-disk file keeps
                # 'session_id'; see the docstring above.
                'coding_session_id': data['session_id'],
                'created_at': data['created_at'],
                'last_modified': data['last_modified'],
                'description': data.get('description', ''),
                'suggestion_count': data['statistics']['total_suggestions'],
                'approved_count': data['statistics']['approved'],
                'rejected_count': data['statistics']['rejected'],
                'pending_count': data['statistics']['pending'],
                # The project's folder name, not "data" (v0.14)
                'project_name': self.project_name(project_db),
                'project_path': project_db,
                'kept_in': kept_in,
            })

        try:
            project = self.open_project_folder()
            in_project = set()
            if project is not None and (
                    not wanted or self.same_project(project / "data.qda",
                                                    wanted)):
                project_read = True
                project_db = str(project / "data.qda")
                # Every entry at a session's name is that session, as a
                # lookup takes it, though one that cannot be read (a link,
                # past the cap) is not listed. A folder there that cannot
                # be read is refused with its reason, as a lookup gives it
                try:
                    names = private_files.session_names(
                        project, files_only=False, refuse=True)
                except private_files.PrivateFilesError as e:
                    names, folder_refusal = [], str(e)
                for name in names:
                    sid = name[len("session_"):-len(".json")]
                    in_project.add(sid)
                    try:
                        data = json.loads(private_files.read_session(
                            project, name).decode("utf-8"))
                        listed(data, sid, project_db, KEPT_IN_PROJECT)
                    except Exception:
                        skipped["unreadable"] += 1
                        not_read[KEPT_IN_PROJECT] += 1
            for filepath in self.storage_dir.glob("session_*.json"):
                # An id the project's folder holds is that session there,
                # as a lookup takes it: a copy here is not listed again
                if filepath.stem[len("session_"):] in in_project:
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    listed(data, filepath.stem[len("session_"):],
                           data['project_path'], KEPT_ON_THIS_COMPUTER)
                except Exception:
                    skipped["unreadable"] += 1
                    not_read[KEPT_ON_THIS_COMPUTER] += 1
                    continue

            # Sort by last modified (most recent first)
            sessions.sort(key=lambda x: x['last_modified'], reverse=True)

        except Exception as e:
            logger.error(f"Error listing sessions: {error_label(e)}")
            raise

        # Counts only: a file's name can carry a person's or a computer's
        # name (a sync service's conflicted copy)
        if skipped["another_id"]:
            logger.warning("Skipped %d session file(s) holding another "
                           "session's id", skipped["another_id"])
        if skipped["unreadable"]:
            logger.warning("Skipped %d session file(s) that could not be "
                           "read", skipped["unreadable"])
        if folder_refusal is not None:
            logger.warning("The open project's sessions folder could not be "
                           "read, so its sessions were not listed")
        return SessionsListing(sessions, folder_refusal,
                               not_read[KEPT_IN_PROJECT],
                               not_read[KEPT_ON_THIS_COMPUTER], project_read)

    def project_sessions(self, project_db: Any
                         ) -> List[Tuple[str, AICodingSession, bytes]]:
        """A project's coding sessions from both places (v0.15.4), each
        with its id and the bytes it was read with, in the order of
        their ids: those kept in its sessions folder while it is the open
        project, and those in the state folder that record it. Every one
        is listed, with no stop; a file that cannot be read is passed
        over, since it cannot be applied either. For delete_coding's
        marks, undo's check and its marks, each saving a session at its
        place only if unchanged."""
        found: Dict[str, Tuple[str, AICodingSession, bytes]] = {}
        project = self.open_project_folder()
        if project is not None and self.same_project(project_db,
                                                     project / "data.qda"):
            for name in private_files.session_names(project):
                sid = name[len("session_"):-len(".json")]
                try:
                    session, raw = self.load_session_and_bytes(sid)
                except Exception:
                    continue
                if session.kept_in == KEPT_IN_PROJECT:
                    found[sid] = (sid, session, raw)
        for path in sorted(self.storage_dir.glob("session_*.json")):
            sid = path.stem[len("session_"):]
            if sid in found:
                continue
            try:
                session, raw = self.load_session_and_bytes(sid)
            except Exception:
                continue
            if session.kept_in == KEPT_ON_THIS_COMPUTER and \
                    self.same_project(session.project_path, project_db):
                found[sid] = (sid, session, raw)
        return [found[sid] for sid in sorted(found)]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file: the one the lookup finds (v0.15.4), in
        the open project's sessions folder, with that session's temporary
        files there, else in the state folder; never the other place's.
        A link or anything but a file at the id's name in the project is
        refused with the reason, and the state folder's file of that id
        left as it is.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found.
            Returns False for invalid session ID formats.
        """
        try:
            self._validate_session_id(session_id)
        except ValueError:
            return False
        name = self.file_name(session_id)
        project = self.open_project_folder()
        refusal = None
        if self._project is not None and project is None:
            refusal = self._no_project_refusal()
        if project is not None:
            try:
                if private_files.remove_session(project, name):
                    logger.info(f"Deleted session {session_id}")
                    return True
            except private_files.PrivateFilesError as e:
                if not e.about_folder:
                    logger.error(f"Failed to delete session {session_id}: "
                                 f"{error_label(e)}")
                    raise SessionFileError(e.code, str(e)) from None
                refusal = self._folder_refusal(e)
        filepath = self.storage_dir / name
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"Deleted session {session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {error_label(e)}")
                raise
        if refusal is not None:
            raise refusal
        return False
