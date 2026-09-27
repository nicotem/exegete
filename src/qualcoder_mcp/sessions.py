# SPDX-License-Identifier: LGPL-3.0-or-later
"""Session management for AI coding suggestions with disk persistence."""

import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

from .database import error_label

logger = logging.getLogger(__name__)


# How the words of a passage carry a suggested code (owner ruling 21,
# v0.14): a category, never a number. `explicit`: the passage states it;
# `interpretive`: the assistant is reading into it. A suggestion recorded
# before v0.14 carried a 0-1 "confidence" instead; it loads with no label
# (None), and the number is not kept.
SUPPORT_LABELS = {
    "explicit": "the passage states it",
    "interpretive": "the assistant is reading into it",
}


def support_label(value: Any) -> Optional[str]:
    """The label a value names ('explicit' or 'interpretive'), or None.

    Only a string can name one: a list, a number or a boolean is no label
    (and a list cannot even be looked up in a dict)."""
    return value if isinstance(value, str) and value in SUPPORT_LABELS else None


def support_in_words(support: Optional[str]) -> Optional[str]:
    """'explicit (the passage states it)', or None for no label."""
    label = support_label(support)
    if label is None:
        return None
    return f"{label} ({SUPPORT_LABELS[label]})"


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


def unique_in_order(values: Optional[List[Any]]) -> List[Any]:
    """Each value once, first mention first: a GUID named twice in one
    list is one decision, and is counted once."""
    out: List[Any] = []
    for value in (values or []):
        if value not in out:
            out.append(value)
    return out


def memo_with_support(reasoning: str, support: Optional[str]) -> str:
    """The text an applied suggestion carries in its coding memo, and in a
    REFI-QDA export's selection description: the support label in words
    FIRST, then the reason. First, because a reason holding QualCoder's
    '#####' private marker keeps only what comes before it, and the label
    must survive that. No label (a pre-v0.14 suggestion, or a coding read
    back from the project for an export): the text exactly as given, not
    trimmed, since a project export carries every memo as QualCoder
    stores it. Never a number (owner ruling 21)."""
    label = support_in_words(support)
    if label is None:
        return reasoning or ""
    parts = [f"Support: {label}", (reasoning or "").strip()]
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
        support: Optional[str] = None,
        status: str = "pending",
        context_before: str = "",
        context_after: str = "",
        guid: Optional[str] = None,
        span_alternatives: Optional[List[Dict[str, Any]]] = None,
        adjusted: bool = False,
        applied_ctid: Optional[int] = None,
        support_cleared: bool = False,
        context_from_file: bool = False
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
        self.support = support_label(support)
        # True when edit_suggestion moved the suggestion to another code
        # without a new label: the old one was given for the old code, so
        # it is cleared rather than carried (fix round 1)
        self.support_cleared = bool(support_cleared) and self.support is None
        # True once this server took context_before/after from the file
        # (v0.14 on); before, the assistant could supply them, so an older
        # suggestion's stored context is not shown when it cannot be
        # re-read from the file (fix round 1)
        self.context_from_file = bool(context_from_file)
        # 'pending', 'approved', 'rejected', 'applied', or 'removed' (it
        # was applied, then its coding was deleted with delete_coding)
        self.status = status
        self.context_before = context_before  # Text before for context
        self.context_after = context_after  # Text after for context
        self.guid = guid or str(uuid.uuid4())
        # Server-computed ready-made span adjustments (shorter/longer).
        # Presentational only: use_alternative recomputes from the current
        # fulltext at edit time. [] for pre-v0.8 sessions (zero migration).
        self.span_alternatives = span_alternatives or []
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
            "support": self.support,
            "status": self.status,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "guid": self.guid,
            "span_alternatives": self.span_alternatives,
            "adjusted": self.adjusted,
            "applied_ctid": self.applied_ctid,
            "support_cleared": self.support_cleared,
            "context_from_file": self.context_from_file
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
            # "support": it loads with no label, and the number is dropped
            support=data.get("support"),
            status=data.get("status", "pending"),
            context_before=data.get("context_before", ""),
            context_after=data.get("context_after", ""),
            guid=data.get("guid"),
            span_alternatives=data.get("span_alternatives"),
            adjusted=data.get("adjusted", False),
            applied_ctid=data.get("applied_ctid"),
            support_cleared=data.get("support_cleared", False),
            context_from_file=data.get("context_from_file", False) is True
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
        self.merged_into = merged_into      # the target's GUID, once merged

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
            example_segments=data.get("example_segments", []),
            collides_with=data.get("collides_with"),
            created_code_id=data.get("created_code_id"),
            guid=data.get("guid"),
            merged_into=data.get("merged_into"),
        )


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
        # note: those sessions keep that behaviour.
        self.scope = self._clean_scope(scope)
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
        return {"file_ids": file_ids, "code_ids": code_ids}

    def outside_scope(self, file_id: int,
                      code_id: Optional[int] = None) -> Optional[str]:
        """Which part of the scope a file or code falls outside, or None.

        'file' or 'code'; None when the session has no scope (made before
        v0.14) or both are inside it. code_id None checks the file only."""
        if self.scope is None:
            return None
        if file_id not in self.scope["file_ids"]:
            return "file"
        codes = self.scope["code_ids"]
        if code_id is not None and codes is not None and code_id not in codes:
            return "code"
        return None

    def add_codes_to_scope(self, code_ids: List[int]) -> None:
        """Codes created from this session's approved proposals join a
        session limited to named codes, so the loop can apply them."""
        if self.scope is not None and self.scope["code_ids"] is not None:
            for cid in code_ids:
                if cid not in self.scope["code_ids"]:
                    self.scope["code_ids"].append(cid)

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
            "scope": self.scope,
            "ai_coder_name_at_record": self.ai_coder_name_at_record,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "proposed_codes": [p.to_dict() for p in self.proposed_codes],
            "span_edit_stats": self.span_edit_stats,
            "statistics": self.get_statistics(),
            "proposal_statistics": self.proposal_statistics()
        }

    _REQUIRED_FIELDS = {
        "project_path", "session_id", "created_at", "last_modified"
    }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AICodingSession':
        """Create session from dictionary.

        Raises:
            ValueError: If required fields are missing
            TypeError: If data is not a dictionary
        """
        if not isinstance(data, dict):
            raise TypeError("AICodingSession data must be a dictionary")

        missing = cls._REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Missing required session fields: {missing}")

        session = cls(
            project_path=data["project_path"],
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


class SessionManager:
    """Manage AI coding sessions with disk persistence."""

    # Session IDs must be valid UUID4 strings (hex + hyphens only)
    _SESSION_ID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )

    def __init__(self, storage_dir: str = "~/.qualcoder_mcp/sessions"):
        # Constructing a manager must not touch the disk: the server
        # builds one at import time, and `qualcoder-mcp --version` would
        # otherwise create the storage directory before it had even read
        # its own command line (v0.12 fix round 1, F16). The directory is
        # created on the first save; every read path copes with its
        # absence (a glob over a missing directory yields nothing).
        self.storage_dir = Path(storage_dir).expanduser()
        logger.debug("SessionManager storage ready")

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
        """Save session to disk as JSON, atomically and owner-only.

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
        (H5, B4.5).

        Args:
            session: The AICodingSession to save

        Raises:
            ValueError: If session ID is not valid UUID4 format
        """
        self._validate_session_id(session.session_id)
        self._ensure_storage_dir()
        filepath = self.storage_dir / f"session_{session.session_id}.json"
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

    def load_session_and_bytes(self, session_id: str):
        """Load a session and return it with the file's bytes as read.

        One read serves both, so a caller can later tell whether another
        writer (a second host on the same project) saved the file in the
        meantime (save_session_if_unchanged). A file whose inner id is not
        its name is refused: saving it would write the session its inner
        id names, not the file that was read (fix round 1).

        Raises:
            ValueError: If the id is not UUID4, or the file holds another id
            FileNotFoundError: If session file doesn't exist
        """
        self._validate_session_id(session_id)
        filepath = self.storage_dir / f"session_{session_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Session {session_id} not found at {filepath}")

        try:
            raw = filepath.read_bytes()
            data = json.loads(raw.decode("utf-8"))
            session = AICodingSession.from_dict(data)
            if session.session_id != session_id:
                raise ValueError(
                    f"Session file for {session_id} holds another session's "
                    f"id; it is refused rather than used or written")
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
        window left is the one between this comparison and the replace."""
        filepath = self.storage_dir / f"session_{session.session_id}.json"
        try:
            if filepath.read_bytes() != raw:
                return False
        except OSError:
            return False
        self.save_session(session)
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a session file exists.

        Args:
            session_id: The session ID to check

        Returns:
            True if session file exists, False otherwise.
            Returns False for invalid session ID formats.
        """
        try:
            self._validate_session_id(session_id)
        except ValueError:
            return False
        filepath = self.storage_dir / f"session_{session_id}.json"
        return filepath.exists()

    def list_sessions(
        self,
        project_path: Optional[str] = None,
        days_old: int = 30
    ) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by project and age.

        Args:
            project_path: Filter by specific project path (optional)
            days_old: Only show sessions from last N days (default: 30)

        Returns:
            List of session metadata dictionaries. Each entry carries the
            API-facing key ``coding_session_id``; the on-disk files keep
            their own ``session_id`` key, which ``load_session`` and
            ``cleanup_old_sessions`` continue to read.
        """
        sessions = []
        cutoff_date = datetime.now() - timedelta(days=days_old)

        try:
            for filepath in self.storage_dir.glob("session_*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Filter by project if specified
                    if project_path and data['project_path'] != project_path:
                        continue

                    # Filter by age
                    last_modified = datetime.fromisoformat(data['last_modified'])
                    if last_modified < cutoff_date:
                        continue

                    # Get project name
                    project_name = Path(data['project_path']).stem

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
                        'project_name': project_name,
                        'project_path': data['project_path']
                    })
                except Exception as e:
                    logger.warning(f"Skipping invalid session file "
                                   f"{filepath.name}: {error_label(e)}")
                    continue

            # Sort by last modified (most recent first)
            sessions.sort(key=lambda x: x['last_modified'], reverse=True)

        except Exception as e:
            logger.error(f"Error listing sessions: {error_label(e)}")
            raise

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file.

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
        filepath = self.storage_dir / f"session_{session_id}.json"
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"Deleted session {session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {error_label(e)}")
                raise
        return False

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Delete sessions older than specified days.

        Args:
            days_old: Delete sessions older than N days

        Returns:
            Count of deleted sessions
        """
        deleted = 0
        cutoff_date = datetime.now() - timedelta(days=days_old)

        try:
            for filepath in self.storage_dir.glob("session_*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    last_modified = datetime.fromisoformat(data['last_modified'])
                    if last_modified < cutoff_date:
                        filepath.unlink()
                        deleted += 1
                        logger.info(f"Deleted old session {data['session_id']}")
                except Exception as e:
                    logger.warning(f"Error processing {filepath.name} during "
                                   f"cleanup: {error_label(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error during session cleanup: {error_label(e)}")
            raise

        logger.info(f"Cleaned up {deleted} old sessions")
        return deleted
