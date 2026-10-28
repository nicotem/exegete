# SPDX-License-Identifier: LGPL-3.0-or-later
"""Undo (v0.15.2): take back changes Exegete made, each whole or not at all.

A change's record (change_record.py) gives the rows it touched, by table
and key, with keyed digests of each row before and after the change.
`plan` reads the records, newest first, and judges each change against
the project and its coding sessions as the undo would leave them: on the
read-only connection for the preview, and again on the write connection
under SQLite's write lock, where `write` then puts the rows back from
each change's own backup. Nothing here writes but `write`.

A change is refused, whole, when a row it touched has been changed since
(judged by the rows' content), when later work depends on a row it would
remove, in the project or in a coding session, or when a row it would put
back or set back would no longer fit: its key or a unique value taken, a
row it points at gone, or another row in its place under the same id, a
loop in the tree of categories or of codes. Each value crosses from the
backup with its storage class and its bytes, nothing decoded.

A refusal here is a reason and its counts, never a value, a name or a
path; the words are server.py's (UNDO_REFUSAL_TEXTS).
"""

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Set, Tuple

from . import change_record
from .database import (POSITIONED_TABLES, _quoted, _sqlite_ro_immutable_uri,
                       backup_database_is_link, is_this_servers_backup_name,
                       unclean_backup_side_files, validate_qda_path)
from .sessions import SessionManager

# ---------------------------------------------------------------------------
# The reasons a change cannot be undone, each with the words server.py gives
# ---------------------------------------------------------------------------
RECEIPT_UNKNOWN = "receipt_unknown"
ANOTHER_PROJECT = "another_project"
SECRET_REPLACED = "secret_replaced"
NEWER_FORMAT = "newer_format"
RECORD_UNREADABLE = "unreadable_record"
TOO_OLD = "too_old"
DATED_AHEAD = "dated_ahead"
NOT_YET_UNDOABLE = "not_yet_undoable"
OWN_TRIGGERS = "own_triggers"
BACKUP_GONE = "backup_gone"
BACKUP_UNCLEAN = "backup_unclean"
BACKUP_UNREADABLE = "backup_unreadable"
BACKUP_CHANGED = "backup_changed"
CHANGED_SINCE = "changed_since"
PROJECT_ROW_CHANGED = "project_row_changed"
SCHEMA_CHANGED = "schema_changed"
TEXT_CHANGED = "text_changed"
DEPENDED_ON = "depended_on"
SUGGESTIONS_DEPEND = "suggestions_depend"
KEY_IN_USE = "key_in_use"
VALUE_TAKEN = "value_taken"
PARENT_GONE = "parent_gone"
PARENT_REPLACED = "parent_replaced"
DOCUMENTS_CLASH = "documents_clash"
LOOP = "loop"

# The tools whose changes take a route of their own back, which the third
# undo design adds: refused here until it lands
NOT_YET_UNDOABLE_TOOLS = frozenset({
    "pseudonymise_source", "import_documents", "set_project_coder_name",
    "save_names_list"})
# The tools whose marks in a coding session an undo sets back, each with
# the kind of mark: an apply's suggestions to approved, a creation's
# proposals to approved, a deleted coding's suggestion to applied
SESSION_MARKS = {"apply_codings": "approved",
                 "create_proposed_codes": "proposals",
                 "delete_coding": "applied"}
# How far ahead of the clock a record may be dated and still be judged
CLOCK_SLACK_SECONDS = 300
# How many values one statement binds when rows are read by key
CHUNK = 400

# The kinds of row a change left, and what the undo does with each
ADDED, CHANGED, REMOVED = "added", "changed", "removed"
UNDO_KIND = {ADDED: "removed", CHANGED: "set_back", REMOVED: "put_back"}


# ---------------------------------------------------------------------------
# What points at what, from the format (new_project.TABLES)
# ---------------------------------------------------------------------------

class Reference(NamedTuple):
    """Columns of one table that hold the key, or the name, of a row of
    another: `when` limits it to rows whose column holds a value (an
    attribute value's kind of entity, a graph memo's kind of source)."""
    table: str
    columns: Tuple[str, ...]
    target: str
    target_columns: Tuple[str, ...]
    when: Optional[Tuple[str, str]] = None


def _ref(table: str, column: str, target: str, target_column: str,
         when: Optional[Tuple[str, str]] = None) -> Reference:
    return Reference(table, (column,), target, (target_column,), when)


_FREE_LINE_ENDS = (("freetextid", "gr_free_text_item", "freetextid"),
                   ("catid", "code_cat", "catid"),
                   ("cid", "code_name", "cid"),
                   ("caseid", "cases", "caseid"),
                   ("fileid", "source", "id"),
                   ("imid", "code_image", "imid"),
                   ("avid", "code_av", "avid"))
# QualCoder 4.0's memo nodes on graphs, by their kind of source
# (view_graph.py, MemoGraphicsItem, at b95e021)
_MEMO_SOURCES = (("code", "code_name", "cid"), ("category", "code_cat", "catid"),
                 ("code_text", "code_text", "ctid"),
                 ("code_image", "code_image", "imid"),
                 ("code_av", "code_av", "avid"), ("case", "cases", "caseid"),
                 ("file", "source", "id"))

REFERENCES: Tuple[Reference, ...] = (
    # codings of the three kinds, to their code and their file; a text
    # coding to its audio or video coding
    _ref("code_text", "cid", "code_name", "cid"),
    _ref("code_text", "fid", "source", "id"),
    _ref("code_text", "avid", "code_av", "avid"),
    _ref("code_image", "cid", "code_name", "cid"),
    _ref("code_image", "id", "source", "id"),
    _ref("code_av", "cid", "code_name", "cid"),
    _ref("code_av", "id", "source", "id"),
    # the trees of codes and of categories
    _ref("code_name", "catid", "code_cat", "catid"),
    _ref("code_name", "supercid", "code_name", "cid"),
    _ref("code_cat", "supercatid", "code_cat", "catid"),
    # case links
    _ref("case_text", "caseid", "cases", "caseid"),
    _ref("case_text", "fid", "source", "id"),
    # attribute values: to their case, file or journal entry by their kind
    # (for a journal entry, attribute.id is its jid), and by name to their
    # type, whose caseOrFile is the value's kind
    _ref("attribute", "id", "cases", "caseid", ("attr_type", "case")),
    _ref("attribute", "id", "source", "id", ("attr_type", "file")),
    _ref("attribute", "id", "journal", "jid", ("attr_type", "journal")),
    Reference("attribute", ("name", "attr_type"), "attribute_type",
              ("name", "caseOrFile")),
    # a transcript to its recording; notes to their file
    _ref("source", "av_text_id", "source", "id"),
    _ref("annotation", "fid", "source", "id"),
    # the saved graphs
    _ref("gr_cdct_text_item", "grid", "graph", "grid"),
    _ref("gr_cdct_text_item", "supercatid", "code_cat", "catid"),
    _ref("gr_cdct_text_item", "catid", "code_cat", "catid"),
    _ref("gr_cdct_text_item", "cid", "code_name", "cid"),
    _ref("gr_case_text_item", "grid", "graph", "grid"),
    _ref("gr_case_text_item", "caseid", "cases", "caseid"),
    _ref("gr_file_text_item", "grid", "graph", "grid"),
    _ref("gr_file_text_item", "fid", "source", "id"),
    _ref("gr_free_text_item", "grid", "graph", "grid"),
    _ref("gr_free_text_item", "ctid", "code_text", "ctid"),
    _ref("gr_free_text_item", "memo_ctid", "code_text", "ctid"),
    _ref("gr_free_text_item", "memo_imid", "code_image", "imid"),
    _ref("gr_free_text_item", "memo_avid", "code_av", "avid"),
    _ref("gr_cdct_line_item", "grid", "graph", "grid"),
    _ref("gr_cdct_line_item", "fromcatid", "code_cat", "catid"),
    _ref("gr_cdct_line_item", "fromcid", "code_name", "cid"),
    _ref("gr_cdct_line_item", "tocatid", "code_cat", "catid"),
    _ref("gr_cdct_line_item", "tocid", "code_name", "cid"),
    _ref("gr_free_line_item", "grid", "graph", "grid"),
    *(_ref("gr_free_line_item", end + column, target, target_column)
      for end in ("from", "to")
      for column, target, target_column in _FREE_LINE_ENDS),
    _ref("gr_memo_item", "grid", "graph", "grid"),
    *(_ref("gr_memo_item", "memo_source_id", target, target_column,
           ("memo_source_type", kind))
      for kind, target, target_column in _MEMO_SOURCES),
    _ref("gr_pix_item", "grid", "graph", "grid"),
    _ref("gr_pix_item", "imid", "code_image", "imid"),
    _ref("gr_av_item", "grid", "graph", "grid"),
    _ref("gr_av_item", "avid", "code_av", "avid"),
)

# The references from each table, by the table's name in lower case
REFERENCES_FROM: Dict[str, Tuple[Reference, ...]] = {}
for _reference in REFERENCES:
    REFERENCES_FROM[_reference.table] = REFERENCES_FROM.get(
        _reference.table, ()) + (_reference,)
del _reference

# The order rows are put back in, parents first; rows are removed in the
# opposite order, children first. A table not named here comes last.
TABLE_ORDER = (
    "project", "coder_names", "attribute_type", "journal", "source", "cases",
    "code_cat", "code_name", "code_av", "code_image", "code_text",
    "annotation", "case_text", "attribute", "graph", "gr_cdct_text_item",
    "gr_case_text_item", "gr_file_text_item", "gr_free_text_item",
    "gr_cdct_line_item", "gr_free_line_item", "gr_memo_item", "gr_pix_item",
    "gr_av_item", "stored_sql", "manage_files_display", "files_filter")
# The trees a parent column builds: (table, its key, the parent column)
TREES = (("code_cat", "catid", "supercatid"), ("code_name", "cid", "supercid"))
# The tables whose rows sit at places in a file's text, by `fid`
CODING_TABLES = ("code_text", "code_image", "code_av")


# ---------------------------------------------------------------------------
# A value as it crosses: its storage class and its bytes, never decoded
# ---------------------------------------------------------------------------

class Value(NamedTuple):
    """One stored value: SQLite's `typeof`, its bytes as `CAST(... AS
    BLOB)` gives them (what every digest is made over, as the capture
    makes it), and for a number the number SQLite gives, which is what
    is written back. A text is written back as `CAST(? AS TEXT)` over
    its bytes, so a note that is not UTF-8 crosses unchanged."""
    kind: str
    raw: Optional[bytes]
    number: Any


NULL = Value("null", None, None)


def _read_sql(column: str, prefix: str = "") -> str:
    """The three expressions a Value is read from."""
    c = f"{prefix}{_quoted(column)}"
    return (rf"typeof({c}), CAST({c} AS BLOB), "
            rf"CASE WHEN typeof({c}) IN ('integer', 'real') THEN {c} END")


def _values(row: Sequence[Any], start: int, columns: Sequence[str]
            ) -> Dict[str, Value]:
    """The Values of `columns` from a row read with `_read_sql`, from
    position `start`."""
    out = {}
    for i, column in enumerate(columns):
        kind, raw, number = row[start + 3 * i: start + 3 * i + 3]
        if raw is not None and not isinstance(raw, bytes):
            raw = bytes(raw)
        out[column] = Value(str(kind), raw, number)
    return out


def same_value(a: Value, b: Value) -> bool:
    """Whether two values are equal as SQLite's `=` compares a key or a
    unique value: two numbers by their number, anything else by its
    storage class and its bytes; NULL equals nothing."""
    if a.kind == "null" or b.kind == "null":
        return False
    if a.kind in ("integer", "real") and b.kind in ("integer", "real"):
        return a.number == b.number
    return a.kind == b.kind and a.raw == b.raw


def points_at_nothing(value: Value) -> bool:
    """A reference that names no row: NULL, or an id below 1, which
    QualCoder uses for "none" (a graph's free text with no coding is -1)
    and SQLite never gives a row."""
    if value.kind == "null":
        return True
    return value.kind in ("integer", "real") and value.number < 1


def bind(value: Value) -> Tuple[int, Any]:
    """A value as `_write_sql`'s pair of parameters: whether it is a text
    (then CAST over its bytes), and what is bound."""
    if value.kind == "text":
        return 1, value.raw if value.raw is not None else b""
    if value.kind == "blob":
        return 0, value.raw if value.raw is not None else b""
    if value.kind in ("integer", "real"):
        return 0, value.number
    return 0, None


def _write_sql(start: int) -> str:
    """The placeholder for one value from parameter `start`: a text cast
    from its bytes, anything else as bound."""
    return rf"CASE WHEN ?{start} THEN CAST(?{start + 1} AS TEXT) ELSE ?{start + 1} END"


def text_of(value: Optional[Value]) -> Optional[str]:
    """A text value decoded for a reader that needs a name (an owner, a
    file's name), None when it is not a text; letters that are not UTF-8
    replaced, never sent anywhere but to a count or a comparison."""
    if value is None or value.kind != "text" or value.raw is None:
        return None
    return value.raw.decode("utf-8", "replace")


def integer_of(value: Optional[Value]) -> Optional[int]:
    if value is None or value.kind != "integer":
        return None
    return int(value.number)


# ---------------------------------------------------------------------------
# The digests, made as the capture makes them (database._digest_sql)
# ---------------------------------------------------------------------------

class Digests:
    """change_record.row_function, called in Python: nothing is
    registered on a connection."""

    def __init__(self, secret: str):
        self._fn = change_record.row_function(secret)

    def row(self, columns: Sequence[str], values: Dict[str, Value]
            ) -> Optional[str]:
        """A row's digest over `columns`, None when one is missing."""
        pairs: List[Any] = []
        for column in columns:
            value = values.get(column)
            if value is None:
                return None
            pairs += [value.kind, value.raw]
        found = self._fn("row", *pairs)
        return None if found == change_record.UNREADABLE else found

    def key(self, value: Value) -> Optional[str]:
        if value.kind == "null":
            return None
        found = self._fn("key", value.kind, value.raw)
        return None if found == change_record.UNREADABLE else found

    def text(self, value: Optional[Value]) -> Optional[str]:
        if value is None:
            return None
        found = self._fn("text", value.kind, value.raw)
        return None if found == change_record.UNREADABLE else found


# ---------------------------------------------------------------------------
# Rows read by key, from the project or from a backup
# ---------------------------------------------------------------------------

Row = Dict[str, Value]


class BackupUnreadable(Exception):
    """A backup's database failed part way through a read, as when a page
    of one of its tables is damaged while its schema reads: the change is
    refused, its backup unreadable, rather than answered as an error of
    the project."""


def _equal_sql(column: str, value: Value, number: int) -> Tuple[str, Any]:
    """`column = <value>` with the value bound as it is stored, and its
    parameter."""
    if value.kind == "text":
        return rf"{_quoted(column)} = CAST(?{number} AS TEXT)", value.raw
    if value.kind in ("integer", "real"):
        return rf"{_quoted(column)} = ?{number}", value.number
    return rf"{_quoted(column)} = ?{number}", value.raw


class Source:
    """One database's rows, read by key: the project, on the connection
    the plan runs on, or a backup, on its own connection. A table's
    columns are read from the database itself; its rows are read with
    every column as Values. Nothing is written. A backup's read that
    fails raises BackupUnreadable; the project's raises SQLite's error."""

    def __init__(self, conn: sqlite3.Connection, digests: Digests,
                 backup: bool = False):
        self.conn = conn
        self.digests = digests
        self.backup = backup
        self._names: Optional[Dict[str, str]] = None
        self._columns: Dict[str, Tuple[str, ...]] = {}
        self._by_digest: Dict[str, Dict[str, Row]] = {}
        self._one_row: Dict[str, List[Row]] = {}

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> List[Tuple]:
        cur = self.conn.cursor()
        try:
            cur.row_factory = None
            return [tuple(row) for row in cur.execute(sql, params)]
        except sqlite3.Error:
            if self.backup:
                raise BackupUnreadable() from None
            raise
        finally:
            cur.close()

    def table(self, name: str) -> Optional[str]:
        """The table's name as the database spells it, None when it has
        no such table."""
        if self._names is None:
            self._names = {
                str(row[0]).lower(): str(row[0]) for row in self._execute(
                    "SELECT name FROM main.sqlite_master WHERE type = 'table'")}
        return self._names.get(str(name).lower())

    def columns(self, name: str) -> Tuple[str, ...]:
        """Every column of the table now, in order; () when it is gone."""
        actual = self.table(name)
        if actual is None:
            return ()
        if actual not in self._columns:
            self._columns[actual] = tuple(
                str(row[0]) for row in self._execute(
                    "SELECT name FROM pragma_table_info(?, 'main') "
                    "ORDER BY cid", (actual,)))
        return self._columns[actual]

    def _select(self, actual: str, columns: Sequence[str]) -> str:
        return ", ".join(_read_sql(column, "r.") for column in columns)

    def rows(self, name: str, key: Optional[str], key_kind: str,
             keys: Iterable[Any],
             only: Optional[Sequence[str]] = None) -> Dict[Any, Row]:
        """The rows of these keys that are there, every column read, or
        with `only` those columns of a table keyed by an integer."""
        actual = self.table(name)
        wanted = list(dict.fromkeys(keys))
        if actual is None or not wanted:
            return {}
        columns = self.columns(actual)
        if only is not None and key_kind == "integer":
            columns = tuple(c for c in only if c in columns)
        if key_kind == "integer":
            found: Dict[Any, Row] = {}
            select = self._select(actual, columns)
            for start in range(0, len(wanted), CHUNK):
                part = wanted[start:start + CHUNK]
                marks = ", ".join("?" * len(part))
                for row in self._execute(
                        f"SELECT r.{_quoted(key)}, {select} FROM main."
                        f"{_quoted(actual)} AS r WHERE r.{_quoted(key)} "
                        f"IN ({marks})", part):
                    if isinstance(row[0], int):
                        found[row[0]] = _values(row, 1, columns)
            return found
        if key_kind == "digest":
            every = self.by_digest(actual, key)
            return {k: every[k] for k in wanted if k in every}
        if key_kind == "one_row":
            rows = self.one_row(actual)
            return {None: rows[0]} if len(rows) == 1 else {}
        return {}

    def by_digest(self, actual: str, key: Optional[str]) -> Dict[str, Row]:
        """Every row of a table keyed by a unique column, by the digest
        of that column's value, as a record keeps it."""
        if actual not in self._by_digest:
            columns = self.columns(actual)
            found: Dict[str, Row] = {}
            if key in columns:
                for row in self._execute(
                        f"SELECT {self._select(actual, columns)} FROM main."
                        f"{_quoted(actual)} AS r"):
                    values = _values(row, 0, columns)
                    digest = self.digests.key(values[key])
                    if digest is not None:
                        found[digest] = values
            self._by_digest[actual] = found
        return self._by_digest[actual]

    def one_row(self, actual: str) -> List[Row]:
        """The rows of the one-row table (the project row), all of them,
        so that a second row is seen."""
        if actual not in self._one_row:
            columns = self.columns(actual)
            self._one_row[actual] = [
                _values(row, 0, columns) for row in self._execute(
                    f"SELECT {self._select(actual, columns)} FROM main."
                    f"{_quoted(actual)} AS r")]
        return self._one_row[actual]

    def matching(self, name: str, key: Optional[str], key_kind: str,
                 equal: Sequence[Tuple[str, Value]],
                 when: Optional[Tuple[str, str]] = None
                 ) -> Dict[Any, Row]:
        """The rows whose columns hold these values (and, with `when`,
        whose column holds that text), by their key, every column read.
        A value that is NULL matches nothing."""
        actual = self.table(name)
        if actual is None or any(v.kind == "null" for _, v in equal):
            return {}
        columns = self.columns(actual)
        if any(c not in columns for c, _ in equal) or (
                when is not None and when[0] not in columns):
            return {}
        clauses, params = [], []
        for column, value in equal:
            clause, param = _equal_sql(column, value, len(params) + 1)
            clauses.append("r." + clause)
            params.append(param)
        if when is not None:
            clauses.append(rf"r.{_quoted(when[0])} = ?{len(params) + 1}")
            params.append(when[1])
        key_sql = (rf"r.{_quoted(key)}" if key_kind == "integer" else "NULL")
        rows = self._execute(
            f"SELECT {key_sql}, {self._select(actual, columns)} FROM main."
            f"{_quoted(actual)} AS r WHERE {' AND '.join(clauses)}", params)
        found: Dict[Any, Row] = {}
        for row in rows:
            values = _values(row, 1, columns)
            if key_kind == "integer":
                found[row[0]] = values
            elif key_kind == "digest":
                found[self.digests.key(values.get(key, NULL))] = values
            else:
                found[None] = values
        return found

    def matching_in(self, name: str, key: Optional[str], key_kind: str,
                    column: str, numbers: Sequence[Any],
                    when: Optional[Tuple[str, str]] = None
                    ) -> Dict[Any, Row]:
        """The rows whose column holds one of these numbers (ids), by
        their key, every column read, a few hundred numbers a statement."""
        actual = self.table(name)
        if actual is None or not numbers:
            return {}
        columns = self.columns(actual)
        if column not in columns or (when is not None
                                     and when[0] not in columns):
            return {}
        key_sql = (rf"r.{_quoted(key)}" if key_kind == "integer" else "NULL")
        found: Dict[Any, Row] = {}
        wanted = list(dict.fromkeys(numbers))
        for start in range(0, len(wanted), CHUNK):
            part = wanted[start:start + CHUNK]
            params: List[Any] = list(part)
            condition = ""
            if when is not None:
                condition = rf" AND r.{_quoted(when[0])} = ?"
                params.append(when[1])
            for row in self._execute(
                    f"SELECT {key_sql}, {self._select(actual, columns)} "
                    f"FROM main.{_quoted(actual)} AS r WHERE "
                    f"r.{_quoted(column)} IN ({', '.join('?' * len(part))})"
                    f"{condition}", params):
                values = _values(row, 1, columns)
                if key_kind == "integer":
                    found[row[0]] = values
                elif key_kind == "digest":
                    found[self.digests.key(values.get(key, NULL))] = values
                else:
                    found[None] = values
        return found

    def holds(self, name: str, equal: Sequence[Tuple[str, Value]]) -> bool:
        """Whether a row holds these values (a backup asked whether a row
        an undo points at was there before the change)."""
        actual = self.table(name)
        if actual is None or any(v.kind == "null" for _, v in equal):
            return False
        columns = self.columns(actual)
        if any(c not in columns for c, _ in equal):
            return False
        clauses, params = [], []
        for column, value in equal:
            clause, param = _equal_sql(column, value, len(params) + 1)
            clauses.append(clause)
            params.append(param)
        return bool(self._execute(
            f"SELECT 1 FROM main.{_quoted(actual)} WHERE "
            f"{' AND '.join(clauses)} LIMIT 1", params))

    def holds_triggers(self) -> bool:
        return bool(self._execute(
            "SELECT count(*) FROM main.sqlite_master "
            "WHERE type = 'trigger'")[0][0])

    def unique_groups(self, name: str) -> List[Tuple[str, ...]]:
        """The project's own unique groups for a table: each unique index
        that is not partial, by its columns (an expression's index left
        out)."""
        actual = self.table(name)
        if actual is None:
            return []
        groups = []
        for index_name, unique, partial in self._execute(
                'SELECT name, "unique", partial FROM '
                "pragma_index_list(?, 'main')", (actual,)):
            if not unique or partial:
                continue
            columns = [row[0] for row in self._execute(
                "SELECT name FROM pragma_index_info(?, 'main') "
                "ORDER BY seqno", (index_name,))]
            if columns and all(isinstance(c, str) for c in columns):
                groups.append(tuple(columns))
        return groups


# ---------------------------------------------------------------------------
# A record, found and read
# ---------------------------------------------------------------------------

def _hex32(value: Any) -> bool:
    return isinstance(value, str) and change_record.HEX_32.fullmatch(
        value) is not None


def _digest_or_none(value: Any) -> bool:
    return value is None or _hex32(value)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def well_formed(record: Dict[str, Any]) -> bool:
    """Whether a record holds what undo reads, each field of its kind: a
    record edited by hand, or cut short, is refused rather than read. The
    tables and columns it names are checked against the project before
    any of them enters SQL."""
    tables, rows, texts = (record.get("tables"), record.get("rows"),
                           record.get("texts"))
    if not (isinstance(tables, dict) and isinstance(rows, list)
            and isinstance(texts, list) and rows
            and _number(record.get("time"))
            and _digest_or_none(record.get("backup"))
            and (record.get("tool") is None
                 or isinstance(record.get("tool"), str))):
        return False
    for name, entry in tables.items():
        if not (isinstance(name, str) and isinstance(entry, dict)):
            return False
        kind, key = entry.get("key_kind"), entry.get("key")
        columns = entry.get("columns")
        if kind not in ("integer", "digest", "one_row") or not (
                isinstance(columns, list) and columns
                and all(isinstance(c, str) for c in columns)):
            return False
        if (kind == "one_row") != (key is None) or (
                key is not None and key not in columns):
            return False
        if not (entry.get("apart") is None
                or isinstance(entry.get("apart"), str)):
            return False
    for row in rows:
        if not isinstance(row, dict) or row.get("table") not in tables:
            return False
        kind = tables[row["table"]]["key_kind"]
        key = row.get("key")
        if kind == "integer" and not (isinstance(key, int)
                                      and not isinstance(key, bool)):
            return False
        if kind == "digest" and not _hex32(key):
            return False
        if kind == "one_row" and key is not None:
            return False
        before, after = row.get("before"), row.get("after")
        if not (_digest_or_none(before) and _digest_or_none(after)) or (
                before is None and after is None):
            return False
        if kind == "one_row" and (before is None or after is None):
            return False
    for text in texts:
        if not (isinstance(text, dict) and isinstance(text.get("file"), int)
                and not isinstance(text.get("file"), bool)
                and _digest_or_none(text.get("digest"))):
            return False
    return True


class Located(NamedTuple):
    record: Optional[Dict[str, Any]]
    reason: Optional[str]


def locate(project: str, receipt: str, key_check: str,
           clock: Optional[float] = None) -> Located:
    """The record a receipt names, judged: known, of this project, made
    under this secret, of a known format, readable, not dated ahead of
    the clock, under a day old, of a tool whose changes this route takes
    back; or the reason it is not.
    The receipt was checked as 32 lowercase hex characters before any
    path was made."""
    try:
        record = change_record.read(project, receipt)
        if record is None:
            other = change_record.elsewhere(project, receipt)
            if other is None:
                return Located(None, RECEIPT_UNKNOWN)
            return Located(None, SECRET_REPLACED
                           if other.get("key_check") != key_check
                           else ANOTHER_PROJECT)
    except change_record.NewerRecord:
        return Located(None, NEWER_FORMAT)
    if record.get("key_check") != key_check:
        return Located(None, SECRET_REPLACED)
    if record.get("project") != project:
        return Located(None, ANOTHER_PROJECT)
    if record.get("route") != "rows" or not well_formed(record):
        return Located(None, RECORD_UNREADABLE)
    age = (change_record.now() if clock is None else clock) - record["time"]
    if age < -CLOCK_SLACK_SECONDS:
        return Located(None, DATED_AHEAD)
    if age > change_record.KEEP_SECONDS:
        return Located(None, TOO_OLD)
    if record.get("tool") in NOT_YET_UNDOABLE_TOOLS:
        return Located(record, NOT_YET_UNDOABLE)
    return Located(record, None)


def record_counts(record: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """A record's rows by what undoing the change would do to them, then
    by table, read from the record alone."""
    out: Dict[str, Dict[str, int]] = {}
    for row in record.get("rows") or []:
        if not isinstance(row, dict) or not isinstance(row.get("table"), str):
            continue
        what = UNDO_KIND[kind_of(row)]
        out.setdefault(what, {}).setdefault(row["table"], 0)
        out[what][row["table"]] += 1
    return out


def kind_of(row: Dict[str, Any]) -> str:
    """What the change did to a row: added, changed or removed."""
    if row.get("before") is None:
        return ADDED
    if row.get("after") is None:
        return REMOVED
    return CHANGED


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------

class Step(NamedTuple):
    """One row the undo writes: `table` as the project spells it, its key
    as the record keeps it, the key's column and kind, the columns
    written and the values written (None for a row removed), and the row
    as it is now (None for a row put back)."""
    table: str
    key: Any
    key_column: Optional[str]
    key_kind: str
    columns: Tuple[str, ...]
    values: Optional[Row]
    now: Optional[Row]


class ChangePlan:
    """What undoing one change would do, or why it cannot be done."""

    def __init__(self, receipt: str, record: Optional[Dict[str, Any]]):
        self.receipt = receipt
        self.record = record
        self.tool = record.get("tool") if record else None
        self.time = record.get("time") if record else None
        self.refusals: List[Dict[str, Any]] = []
        self.removed: List[Step] = []
        self.put_back: List[Step] = []
        self.set_back: List[Step] = []
        self.fingerprint: Dict[str, Any] = {"receipt": receipt}
        self.suggestions_on_removed_files = 0

    def refuse(self, reason: str, **detail: Any) -> None:
        self.refusals.append({"receipt": self.receipt, "reason": reason,
                              **detail})

    def counts(self) -> Dict[str, Dict[str, int]]:
        """Rows by what the undo does to them, then by table."""
        out: Dict[str, Dict[str, int]] = {}
        for what, steps in (("removed", self.removed),
                            ("put_back", self.put_back),
                            ("set_back", self.set_back)):
            for step in steps:
                out.setdefault(what, {}).setdefault(step.table, 0)
                out[what][step.table] += 1
        return out


class Plan:
    """The whole undo, newest change first: whether it can be done, what
    it writes, and what it sets back in the coding sessions afterwards."""

    def __init__(self):
        self.changes: List[ChangePlan] = []
        self.refusals: List[Dict[str, Any]] = []
        self.overlay: Dict[str, Dict[Any, Optional[Row]]] = {}
        self.checked: Dict[Tuple[str, Any], Tuple[str, Tuple[str, ...]]] = {}
        self.marks: List[Tuple[Any, ...]] = []
        self.removed_codes: Set[int] = set()
        self.removed_files: Set[int] = set()
        self.files_touched: Set[int] = set()
        self.suggestions_on_removed_files = 0

    @property
    def can_run(self) -> bool:
        return bool(self.changes) and not self.refusals

    def fingerprint(self) -> List[Dict[str, Any]]:
        """The signed state: for each change, the digest of its backup's
        name when it needs one and the digest of each row it touched as
        it is now in the project, with each coded file's text."""
        return [change.fingerprint for change in self.changes]


def _norm(value: Value) -> Any:
    """A value as a dictionary key that compares as `same_value` does."""
    if value.kind == "null":
        return None
    if value.kind in ("integer", "real"):
        return ("n", value.number)
    return (value.kind, value.raw)


def _owner_of(row: Optional[Row]) -> Optional[str]:
    return text_of(row.get("owner")) if row else None


def _alike(then: Row, now: Row) -> bool:
    """Whether two rows hold the same values, kind and bytes, in every
    column both have."""
    return all((then[c].kind, then[c].raw) == (now[c].kind, now[c].raw)
               for c in then if c in now)


def _made_together(then: Row, now: Row) -> bool:
    """Whether two rows carry the same date of making, a text that is not
    empty."""
    a, b = then.get("date"), now.get("date")
    return a is not None and b is not None and a.kind == "text" and \
        bool(a.raw) and (a.kind, a.raw) == (b.kind, b.raw)


_MISSING = object()


class _Planner:
    """Builds a Plan on one connection: the project read through it, the
    backups each on a connection of their own, closed at the end."""

    def __init__(self, db_, *, secret: str, project: str,
                 project_db: Path, sessions: Sequence[Tuple[str, Any, bytes]],
                 receipts: Sequence[str],
                 records: Optional[Sequence[Dict[str, Any]]] = None):
        from .database import _capture_table
        self._capture_table = _capture_table
        self.db_ = db_
        self.secret = secret
        self.project_key = project
        self.digests = Digests(secret)
        self.project = Source(db_.conn, self.digests)
        self.project_db = Path(project_db)
        self.sessions = list(sessions)
        self.receipts = set(receipts)
        self.overlay: Dict[str, Dict[Any, Optional[Row]]] = {}
        self._db_rows: Dict[Tuple[str, Any], Optional[Row]] = {}
        self._info: Dict[str, Optional[Tuple[str, Optional[str], str]]] = {}
        self._open: List[sqlite3.Connection] = []
        self._backups: Dict[str, Tuple[Optional[Source], Optional[str]]] = {}
        self.returned: Set[Tuple[Any, Any]] = set()
        self._records = records
        self._index: Optional[Dict[Tuple[str, Any], List[Tuple[Any, ...]]]] = None

    def close(self) -> None:
        for conn in self._open:
            try:
                conn.close()
            except Exception:
                pass
        self._open.clear()

    # -- the project as the undo would leave it so far ----------------------

    def table_info(self, name: str) -> Optional[Tuple[str, Optional[str], str]]:
        """(the project's spelling, the key's column, its kind) for a
        table, read as the capture reads it; None when it is gone."""
        low = str(name).lower()
        if low not in self._info:
            actual = self.project.table(name)
            if actual is None:
                self._info[low] = None
            else:
                table = self._capture_table(self.db_.conn, 0, actual)
                self._info[low] = (actual, table.key, table.key_kind)
        return self._info[low]

    def prefetch(self, actual: str, key_column: Optional[str], key_kind: str,
                 keys: Iterable[Any]) -> None:
        low = actual.lower()
        missing = [k for k in dict.fromkeys(keys)
                   if (low, k) not in self._db_rows]
        if not missing:
            return
        found = self.project.rows(actual, key_column, key_kind, missing)
        for key in missing:
            self._db_rows[(low, key)] = found.get(key)

    def db_row(self, actual: str, key: Any, key_column: Optional[str],
               key_kind: str) -> Optional[Row]:
        mark = (actual.lower(), key)
        if mark not in self._db_rows:
            self.prefetch(actual, key_column, key_kind, [key])
        return self._db_rows[mark]

    def state(self, actual: str, key: Any, key_column: Optional[str],
              key_kind: str) -> Optional[Row]:
        """A row as the undo so far leaves it: the plan's own value where
        an undone change wrote it, the project's otherwise."""
        tab = self.overlay.get(actual.lower())
        if tab is not None and key in tab:
            return tab[key]
        return self.db_row(actual, key, key_column, key_kind)

    def later(self, change: ChangePlan,
              rows: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
        """The later changes, not in this undo, that touched these rows:
        this run's by their receipts, another run's counted."""
        receipts: Dict[str, float] = {}
        others: Set[str] = set()
        for actual, key in rows:
            for when, receipt, run, _whole in self.recorded(actual, key):
                if not _number(when) or change.time is None or \
                        when <= change.time or receipt in self.receipts:
                    continue
                if run == change_record.RUN:
                    receipts[receipt] = when
                else:
                    others.add(receipt)
        out: Dict[str, Any] = {}
        if receipts:
            out["later_changes"] = sorted(receipts, key=receipts.get)
        if others:
            out["other_runs"] = len(others)
        return out

    def recorded(self, actual: str, key: Any) -> List[Tuple[Any, ...]]:
        """The changes Exegete recorded to one row, from every record of
        the project, of any run, read once: (time, receipt, run, whether
        the change added or removed the row)."""
        if self._index is None:
            if self._records is None:
                self._records = change_record.records(self.project_key)
            self._index = {}
            for record in self._records:
                for row in record.get("rows") or []:
                    if isinstance(row, dict) and isinstance(row.get("table"),
                                                            str):
                        try:
                            self._index.setdefault(
                                (row["table"].lower(), row.get("key")),
                                []).append((
                                    record.get("time"), record.get("receipt"),
                                    record.get("run"),
                                    row.get("before") is None
                                    or row.get("after") is None))
                        except TypeError:
                            continue
        try:
            return self._index.get((actual.lower(), key), [])
        except TypeError:
            return []

    # -- the change's backup ------------------------------------------------

    def backup(self, digest: Optional[str]) -> Tuple[Optional[Source],
                                                     Optional[str]]:
        """The change's backup, found by its name's digest among the names
        Exegete gives its backups beside the project, that folder alone
        checked in the restore's order: no journal or link (unclean), a
        database validate_qda_path accepts, then read immutable with no
        wait. (Source, None), or (None, the reason)."""
        if digest is None:
            return None, BACKUP_GONE
        if digest in self._backups:
            return self._backups[digest]
        found = self._find_backup(digest)
        self._backups[digest] = found
        return found

    def _find_backup(self, digest: str) -> Tuple[Optional[Source],
                                                 Optional[str]]:
        folder = self.project_db.parent
        prefix = f"{folder.stem}_backup_"
        try:
            names = sorted(os.listdir(folder.parent))
        except OSError:
            return None, BACKUP_GONE
        match = None
        for name in names:
            if is_this_servers_backup_name(name, prefix) and \
                    change_record.digest(self.secret, "backup", name) == digest:
                match = folder.parent / name
                break
        if match is None:
            return None, BACKUP_GONE
        if match.is_symlink() or unclean_backup_side_files(match) or \
                backup_database_is_link(match):
            return None, BACKUP_UNCLEAN
        try:
            data = validate_qda_path(str(match))
        except Exception:
            return None, BACKUP_UNREADABLE
        if data.parent != match.resolve():
            return None, BACKUP_UNCLEAN
        try:
            conn = sqlite3.connect(_sqlite_ro_immutable_uri(data), uri=True,
                                   timeout=0)
        except sqlite3.Error:
            return None, BACKUP_UNREADABLE
        self._open.append(conn)
        try:
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except sqlite3.Error:
            return None, BACKUP_UNREADABLE
        return Source(conn, self.digests, backup=True), None

    # -- one change ----------------------------------------------------------

    def plan_change(self, change: ChangePlan) -> None:
        """Judge one change against the project as the later changes'
        undo leaves it, then hold what its undo writes over that state."""
        record = change.record
        tables, rows = record["tables"], record["rows"]
        info: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        gone: Dict[str, int] = {}
        for row in rows:
            name = row["table"]
            if name not in info and name not in gone:
                entry = tables[name]
                now = self.table_info(name)
                columns_now = self.project.columns(name)
                if now is None or now[1] != entry["key"] or \
                        now[2] != entry["key_kind"] or any(
                            c not in columns_now for c in entry["columns"]):
                    gone[name] = 0
                else:
                    info[name] = (now[0], entry)
            if name in gone:
                gone[name] += 1
        if gone:
            change.refuse(SCHEMA_CHANGED, rows=gone)
            return
        by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            by_table.setdefault(row["table"], []).append(row)
        for name, its in by_table.items():
            actual, entry = info[name]
            self.prefetch(actual, entry["key"], entry["key_kind"],
                          [r["key"] for r in its])

        # Changed since: each touched row as the undo so far leaves it,
        # against "after", over the columns recorded (a column added since
        # counts only when it holds a value), the project row's coder
        # name set aside; a row the change removed must still be absent
        signed: List[List[Any]] = []
        changed: Dict[str, int] = {}
        in_use: Dict[str, int] = {}
        blocking: List[Tuple[str, Any]] = []
        taken: Set[Tuple[str, Any]] = set()
        project_row = False
        for row in rows:
            actual, entry = info[row["table"]]
            key, columns = row["key"], entry["columns"]
            db_now = self.db_row(actual, key, entry["key"], entry["key_kind"])
            db_digest = None if db_now is None else self.digests.row(
                columns, db_now)
            signed.append([actual, key, db_digest])
            now = self.state(actual, key, entry["key"], entry["key_kind"])
            if kind_of(row) == REMOVED:
                if now is not None:
                    in_use[actual] = in_use.get(actual, 0) + 1
                    blocking.append((actual, key))
                    taken.add((actual, key))
                continue
            digest = db_digest if now is db_now else (
                None if now is None else self.digests.row(columns, now))
            if now is None or digest != row["after"] \
                    or self._filled_since(now, entry):
                changed[actual] = changed.get(actual, 0) + 1
                blocking.append((actual, key))
                project_row = project_row or entry["key_kind"] == "one_row"
        signed_texts, text_changed = [], 0
        source = self.table_info("source")
        for text in record["texts"]:
            now = db_now = None
            if source is not None and source[2] == "integer":
                now = self.state(source[0], text["file"], source[1], "integer")
                db_now = self.db_row(source[0], text["file"], source[1],
                                     "integer")
            digest = None if now is None else self.digests.text(
                now.get("fulltext", NULL))
            signed_texts.append([text["file"], None if db_now is None
                                 else self.digests.text(
                                     db_now.get("fulltext", NULL))])
            if digest != text["digest"]:
                text_changed += 1
        needs_backup = any(kind_of(r) != ADDED for r in rows)
        change.fingerprint.update(
            backup=record.get("backup") if needs_backup else None,
            rows=signed, texts=signed_texts)
        if changed:
            change.refuse(PROJECT_ROW_CHANGED if project_row
                          else CHANGED_SINCE, rows=changed,
                          **self.later(change, blocking))
        if in_use:
            change.refuse(KEY_IN_USE, rows=in_use,
                          **self.later(change, blocking))
        if text_changed:
            change.refuse(TEXT_CHANGED, files=text_changed)

        # The old rows, from the change's own backup, each against
        # "before". Every kind of refusal is counted: a change refused
        # here is still judged for later work that depends on it.
        old: Dict[Tuple[str, Any], Row] = {}
        backup: Optional[Source] = None
        if needs_backup:
            backup, reason = self.backup(record.get("backup"))
            change.fingerprint["backup_found"] = backup is not None
            if reason is not None:
                change.refuse(reason)
            else:
                altered: Dict[str, int] = {}
                try:
                    for name, its in by_table.items():
                        actual, entry = info[name]
                        wanted = [r for r in its if kind_of(r) != ADDED]
                        if not wanted:
                            continue
                        got = backup.rows(name, entry["key"],
                                          entry["key_kind"],
                                          [r["key"] for r in wanted])
                        for r in wanted:
                            values = got.get(r["key"])
                            if values is None or self.digests.row(
                                    entry["columns"], values) != r["before"]:
                                altered[actual] = altered.get(actual, 0) + 1
                            else:
                                old[(name, r["key"])] = values
                except BackupUnreadable:
                    change.refuse(BACKUP_UNREADABLE)
                    old.clear()
                    backup = None
                if altered:
                    change.refuse(BACKUP_CHANGED, rows=altered)

        # What the undo writes, held over the state until the checks pass
        effects: Dict[Tuple[str, Any], Optional[Row]] = {}
        for row in rows:
            name, key = row["table"], row["key"]
            actual, entry = info[name]
            columns = tuple(entry["columns"])
            now = self.state(actual, key, entry["key"], entry["key_kind"])
            kind = kind_of(row)
            if kind == ADDED:
                step = Step(actual, key, entry["key"], entry["key_kind"],
                            columns, None, now)
                change.removed.append(step)
                effects[(actual.lower(), key)] = None
                continue
            if (name, key) not in old or (actual, key) in taken:
                continue
            values = {c: old[(name, key)][c] for c in columns}
            if kind == REMOVED:
                change.put_back.append(Step(actual, key, entry["key"],
                                            entry["key_kind"], columns,
                                            values, None))
                effects[(actual.lower(), key)] = dict(values)
            else:
                change.set_back.append(Step(actual, key, entry["key"],
                                            entry["key_kind"], columns,
                                            values, now))
                post = dict(now or {})
                post.update(values)
                effects[(actual.lower(), key)] = post
        saved = {k: self.overlay.get(k[0], {}).get(k[1], _MISSING)
                 for k in effects}
        for (low, key), values in effects.items():
            self.overlay.setdefault(low, {})[key] = values
        self.check_dependents(change)
        self.check_unique(change)
        try:
            self.check_parents(change, backup)
        except BackupUnreadable:
            change.refuse(BACKUP_UNREADABLE)
        self.check_documents(change)
        self.check_loops(change)
        self.check_sessions(change)
        if change.refusals:
            for (low, key), value in saved.items():
                if value is _MISSING:
                    self.overlay[low].pop(key, None)
                else:
                    self.overlay[low][key] = value

    @staticmethod
    def _filled_since(now: Row, entry: Dict[str, Any]) -> bool:
        """Whether a column the record does not name holds a value: a
        column added since and still empty counts as unchanged (QualCoder
        4.0's first open adds columns to an older project)."""
        known = set(entry["columns"])
        if entry.get("apart"):
            known.add(entry["apart"])
        return any(value.kind != "null" for column, value in now.items()
                   if column not in known)

    # -- the checks, on the project as the undo so far would leave it --------

    def _pointing(self, ref: Reference, info: Tuple[str, Optional[str], str],
                  targets: List[Tuple[Value, ...]]) -> Dict[Any, Row]:
        """The rows that, with the undo so far, point by `ref` at one of
        these targets' values."""
        actual, key, kind = info
        if len(ref.columns) == 1 and all(
                t[0].kind == "integer" for t in targets):
            found_db = self.project.matching_in(
                actual, key, kind, ref.columns[0],
                sorted({t[0].number for t in targets}), ref.when)
        else:
            found_db = {}
            for target in targets:
                found_db.update(self.project.matching(
                    actual, key, kind, list(zip(ref.columns, target)),
                    ref.when))
        tab = self.overlay.get(actual.lower(), {})
        found = {k: row for k, row in found_db.items() if k not in tab}
        wanted = {tuple(_norm(v) for v in t) for t in targets}
        for k, row in tab.items():
            if row is None or (ref.when is not None and text_of(
                    row.get(ref.when[0])) != ref.when[1]):
                continue
            values = tuple(_norm(row.get(c, NULL)) for c in ref.columns)
            if None not in values and values in wanted:
                found[k] = row
        return found

    def check_dependents(self, change: ChangePlan) -> None:
        """Later work that depends on the change: a row that points, by
        REFERENCES, at a row the undo removes, unless the undo removes it
        too or sets it back to point elsewhere."""
        if not change.removed:
            return
        by_target: Dict[str, List[Step]] = {}
        for step in change.removed:
            by_target.setdefault(step.table.lower(), []).append(step)
        found: Dict[Tuple[str, Any], Tuple[str, Row]] = {}
        for ref in REFERENCES:
            steps = by_target.get(ref.target.lower())
            info = self.table_info(ref.table) if steps else None
            if info is None:
                continue
            targets = []
            for step in steps:
                values = tuple(
                    (step.now or {}).get(c, NULL) for c in ref.target_columns)
                if not any(v.kind == "null" for v in values):
                    targets.append(values)
            if not targets:
                continue
            for key, row in self._pointing(ref, info, targets).items():
                found[(info[0].lower(), key)] = (info[0], row)
        if found:
            counts: Dict[str, int] = {}
            for actual, _ in found.values():
                counts[actual] = counts.get(actual, 0) + 1
            change.refuse(DEPENDED_ON, rows=counts,
                          owners=[_owner_of(row) for _, row in found.values()],
                          **self.later(change, [(actual, key) for (
                              _, key), (actual, _) in found.items()]))

    def check_unique(self, change: ChangePlan) -> None:
        """A row put back or set back whose unique values (each unique
        group of the project's own indexes) another row holds."""
        touched: Dict[str, List[Step]] = {}
        for step in change.put_back + change.set_back:
            touched.setdefault(step.table, []).append(step)
        taken: Dict[str, int] = {}
        holders: List[Tuple[str, Any]] = []
        for actual, steps in touched.items():
            key_column, kind = steps[0].key_column, steps[0].key_kind
            tab = self.overlay.get(actual.lower(), {})
            for group in self.project.unique_groups(actual):
                if kind != "one_row" and group == (key_column,):
                    continue
                wanted: Dict[Tuple[Any, ...], List[Any]] = {}
                firsts: Dict[Any, Value] = {}
                for step in steps:
                    post = tab.get(step.key) or {}
                    values = tuple(post.get(c, NULL) for c in group)
                    norm = tuple(_norm(v) for v in values)
                    if None in norm:
                        continue
                    if step.now is not None and norm == tuple(
                            _norm(step.now.get(c, NULL)) for c in group):
                        continue        # its values do not change
                    wanted.setdefault(norm, []).append(step.key)
                    firsts[norm[0]] = values[0]
                if not wanted:
                    continue
                if all(v.kind == "integer" for v in firsts.values()):
                    found_db = self.project.matching_in(
                        actual, key_column, kind, group[0],
                        sorted(v.number for v in firsts.values()))
                else:
                    found_db = {}
                    for value in firsts.values():
                        found_db.update(self.project.matching(
                            actual, key_column, kind, [(group[0], value)]))
                index: Dict[Tuple[Any, ...], Set[Any]] = {}
                for k, row in found_db.items():
                    if k not in tab:
                        index.setdefault(tuple(_norm(row.get(c, NULL))
                                               for c in group), set()).add(k)
                for k, row in tab.items():
                    if row is not None:
                        index.setdefault(tuple(_norm(row.get(c, NULL))
                                               for c in group), set()).add(k)
                for norm, keys in wanted.items():
                    others = index.get(norm, set()) - set(keys)
                    if others or len(keys) > 1:
                        taken[actual] = taken.get(actual, 0) + len(keys)
                        holders += [(actual, k) for k in others]
        if taken:
            change.refuse(VALUE_TAKEN, rows=taken,
                          **self.later(change, holders))

    def _exists(self, ref: Reference, values: Tuple[Value, ...],
                cache: Dict[Any, bool]) -> bool:
        """Whether the row `ref` points at with these values is there, as
        the undo so far would leave the project."""
        mark = (ref.target.lower(), ref.target_columns,
                tuple(_norm(v) for v in values))
        if mark in cache:
            return cache[mark]
        info = self.table_info(ref.target)
        result = False
        if info is not None:
            actual, key, kind = info
            if kind == "integer" and ref.target_columns == (key,) and \
                    values[0].kind == "integer":
                result = self.state(actual, int(values[0].number), key,
                                    kind) is not None
            else:
                tab = self.overlay.get(actual.lower(), {})
                found = self.project.matching(
                    actual, key, kind, list(zip(ref.target_columns, values)))
                result = any(k not in tab for k in found) or any(
                    row is not None and all(
                        same_value(row.get(c, NULL), v)
                        for c, v in zip(ref.target_columns, values))
                    for row in tab.values())
        cache[mark] = result
        return result

    def _numbered(self, ref: Reference, values: Tuple[Value, ...]
                  ) -> Optional[Tuple[str, str, int]]:
        """(the table, its key's column, the id) when `ref` points by the
        integer key of a table keyed by one, else None. SQLite gives such
        an id out again once its row is gone, if it was the highest."""
        info = self.table_info(ref.target)
        if info is None or info[2] != "integer" or \
                ref.target_columns != (info[1],) or \
                values[0].kind != "integer":
            return None
        return info[0], info[1], int(values[0].number)

    def _same_row(self, change: ChangePlan, target: Tuple[str, str, int],
                  backup: Source, cache: Dict[Any, bool]) -> bool:
        """Whether the row under this id, as the undo leaves the project,
        is the row the change's backup holds under it.

        It is not when a later change Exegete recorded, other than one
        this undo takes back, removed or added a row under that id.
        Otherwise it is when the two rows hold the same values in every
        column both have, or the same date of making: a row made since
        carries the date it was made, and neither QualCoder 4.0
        (`code_tree.py`, at b95e021) nor Exegete changes that date when
        it renames, moves or recolours a code or a category or writes
        its memo. A row with no date must hold the same values."""
        actual, key_column, number = target
        mark = (actual.lower(), number)
        if mark not in cache:
            now = self.state(actual, number, key_column, "integer")
            then = backup.rows(actual, key_column, "integer",
                               [number]).get(number)
            cache[mark] = (now is not None and then is not None
                           and not self._made_again(change, actual, number)
                           and (_alike(then, now)
                                or _made_together(then, now)))
        return cache[mark]

    def _made_again(self, change: ChangePlan, actual: str,
                    number: int) -> bool:
        """Whether a change Exegete recorded after this one, not taken back
        by this undo, removed or added a row under this id."""
        return any(
            whole and _number(when) and change.time is not None
            and when > change.time and receipt not in self.receipts
            for when, receipt, _run, whole in self.recorded(actual, number))

    def check_parents(self, change: ChangePlan,
                      backup: Optional[Source]) -> None:
        """A row put back, or a reference a row set back changes, that
        would point at a row gone since, or at another row than before.
        Gone: the change's backup holds the row it pointed at, and the
        project, as the undo leaves it, does not. Another: the project
        holds a row under that id that is not the backup's (`_same_row`),
        since SQLite gives a deleted row's id to the next row made when
        it was the highest. A row placed in a file's text points at its
        file by `fid`, which the digest of the file's text guards
        (TEXT_CHANGED). A reference that pointed at nothing before the
        change goes back as it was."""
        lost: Dict[str, int] = {}
        replaced: Dict[str, int] = {}
        targets: Dict[str, List[Tuple[str, Any]]] = {PARENT_GONE: [],
                                                     PARENT_REPLACED: []}
        cache: Dict[Any, bool] = {}
        same: Dict[Any, bool] = {}
        for step in change.put_back + change.set_back:
            post = self.overlay.get(step.table.lower(), {}).get(step.key)
            if post is None:
                continue
            for ref in REFERENCES_FROM.get(step.table.lower(), ()):
                if ref.when is not None and text_of(
                        post.get(ref.when[0])) != ref.when[1]:
                    continue
                values = tuple(post.get(c, NULL) for c in ref.columns)
                if any(v.kind == "null" for v in values) or (
                        len(values) == 1 and points_at_nothing(values[0])):
                    continue
                if step.now is not None and all(
                        _norm(step.now.get(c, NULL)) == _norm(v)
                        for c, v in zip(ref.columns, values)):
                    continue            # a reference the undo keeps
                if backup is None:
                    continue
                target = self._numbered(ref, values)
                if not self._exists(ref, values, cache):
                    if backup.holds(ref.target, list(zip(
                            ref.target_columns, values))):
                        lost[step.table] = lost.get(step.table, 0) + 1
                        if target is not None:
                            targets[PARENT_GONE].append(target[::2])
                        break
                    continue
                if target is None or (ref.table in POSITIONED_TABLES
                                      and ref.columns == ("fid",)):
                    continue
                if not self._same_row(change, target, backup, same):
                    replaced[step.table] = replaced.get(step.table, 0) + 1
                    targets[PARENT_REPLACED].append(target[::2])
                    break
        for reason, counts in ((PARENT_GONE, lost),
                               (PARENT_REPLACED, replaced)):
            if counts:
                change.refuse(reason, rows=counts,
                              **self.later(change, targets[reason]))

    def check_documents(self, change: ChangePlan) -> None:
        """A text's name set back that a file in the project's documents
        folder now stands for, as rename_file refuses a rename from its
        current name."""
        clashes = 0
        for step in change.set_back:
            if step.table.lower() != "source" or step.now is None:
                continue
            post = self.overlay.get(step.table.lower(), {}).get(step.key) or {}
            name, current = text_of(post.get("name")), text_of(
                step.now.get("name"))
            if name is None or name == current:
                continue
            mediapath = text_of(post.get("mediapath"))
            if mediapath and not mediapath.startswith(("/docs/", "docs:")):
                continue
            if self.db_.documents_clashes(
                    name, own_names=self.db_.own_stored_names(mediapath,
                                                              current)):
                clashes += 1
        if clashes:
            change.refuse(DOCUMENTS_CLASH, files=clashes)

    def check_loops(self, change: ChangePlan) -> None:
        """A parent an undo writes that would make a category, or a code,
        its own ancestor."""
        loops = 0
        for table, key_column, parent_column in TREES:
            info = self.table_info(table)
            if info is None or info[2] != "integer":
                continue
            actual = info[0]
            for step in change.put_back + change.set_back:
                if step.table.lower() != actual.lower():
                    continue
                post = self.overlay.get(actual.lower(), {}).get(step.key) or {}
                parent = integer_of(post.get(parent_column))
                if parent is None or (step.now is not None and integer_of(
                        step.now.get(parent_column)) == parent):
                    continue
                seen: Set[int] = set()
                node: Optional[int] = parent
                while node is not None and node not in seen:
                    if node == step.key:
                        loops += 1
                        break
                    seen.add(node)
                    row = self.state(actual, node, info[1], "integer")
                    node = integer_of(row.get(parent_column)) if row else None
        if loops:
            change.refuse(LOOP, rows=loops)

    def check_sessions(self, change: ChangePlan) -> None:
        """Later work in a coding session: a suggestion naming a code the
        undo removes, in any session of this project, the change's own
        included. SQLite gives a removed code's id to the next code made,
        and apply_codings checks only that the id exists. An applied
        suggestion is never approved again, unless an apply_codings
        undone in the same call returns it to approved. Suggestions
        naming a file the undo removes are counted, not refused:
        apply_codings writes none whose text is not at its place."""
        codes = {step.key for step in change.removed
                 if step.table.lower() == "code_name"
                 and isinstance(step.key, int)}
        files = {step.key for step in change.removed
                 if step.table.lower() == "source"
                 and isinstance(step.key, int)}
        if not codes and not files:
            return
        depending = on_files = 0
        for sid, session, _raw in self.sessions:
            for suggestion in session.suggestions:
                if suggestion.code_id in codes:
                    if suggestion.status == "applied" and (
                            sid, suggestion.guid) not in self.returned:
                        continue
                    depending += 1
                elif suggestion.file_id in files:
                    on_files += 1
        change.suggestions_on_removed_files = on_files
        if depending:
            change.refuse(SUGGESTIONS_DEPEND, suggestions=depending)


# ---------------------------------------------------------------------------
# The plan, whole
# ---------------------------------------------------------------------------

def project_sessions(manager: SessionManager, project_db: Path
                     ) -> List[Tuple[str, Any, bytes]]:
    """This project's coding sessions, each with the bytes it was read
    with, found as delete_coding's marks find them: every session file,
    its project compared by `same_project`; one that cannot be read is
    passed over, since it cannot be applied either."""
    found = []
    for path in sorted(manager.storage_dir.glob("session_*.json")):
        sid = path.stem[len("session_"):]
        try:
            session, raw = manager.load_session_and_bytes(sid)
        except Exception:
            continue
        if SessionManager.same_project(session.project_path, project_db):
            found.append((sid, session, raw))
    return found


def _marks_of(record: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    session, items = record.get("session"), record.get("items")
    if not isinstance(session, str) or not isinstance(items, list):
        return None, []
    return session, [i for i in items if isinstance(i, str)]


def plan(db_, receipts: Sequence[str], *, secret: str, project: str,
         key_check: str, project_db: Path,
         sessions: Sequence[Tuple[str, Any, bytes]],
         clock: Optional[float] = None,
         records: Optional[Sequence[Dict[str, Any]]] = None) -> Plan:
    """The plan for undoing these changes, newest first, read-only.

    `db_` is the connection's database object (the read-only one for the
    preview, the write one under SQLite's write lock); `project` and
    `key_check` are the digests the records keep; `project_db` the
    project's data.qda; `sessions` this project's coding sessions. Each
    receipt was checked as 32 lowercase hex characters before any path
    was made. A change blocked only by a later one in the same call goes
    through after it. `records`, every record of the project, read once
    for a list of several plans, else when a refusal asks which later
    change touched a row."""
    result = Plan()
    planner = _Planner(db_, secret=secret, project=project,
                       project_db=project_db, sessions=sessions,
                       receipts=receipts, records=records)
    try:
        located = []
        for receipt in dict.fromkeys(receipts):
            found = locate(project, receipt, key_check, clock)
            change = ChangePlan(receipt, found.record)
            if found.reason is not None:
                change.refuse(found.reason)
            located.append(change)
        result.changes = sorted((c for c in located if c.record is not None),
                                key=lambda c: c.time, reverse=True)
        ready = [c for c in result.changes if not c.refusals]
        if ready and planner.project.holds_triggers():
            for change in ready:
                change.refuse(OWN_TRIGGERS)
            ready = []
        for change in result.changes:
            if change.tool == "apply_codings":
                session, items = _marks_of(change.record)
                planner.returned |= {(session, guid) for guid in items}
        for change in ready:
            planner.plan_change(change)
        result.refusals = [r for c in located for r in c.refusals]
        result.overlay = planner.overlay
        if result.can_run:
            _gather(result)
    finally:
        planner.close()
    return result


def _gather(result: Plan) -> None:
    """What the write checks before its commit, and what the undo sets
    back after it: the coding sessions' marks, the scopes and the files
    whose reading copies go."""
    for change in result.changes:
        for what, steps in (("removed", change.removed),
                            ("put_back", change.put_back),
                            ("set_back", change.set_back)):
            for step in steps:
                low = step.table.lower()
                result.checked[(low, step.key)] = (step.table, step.columns)
                if low == "code_name" and what == "removed":
                    result.removed_codes.add(step.key)
                if low == "source":
                    result.files_touched.add(step.key)
                    if what == "removed":
                        result.removed_files.add(step.key)
                if low in CODING_TABLES + ("annotation", "case_text"):
                    column = "id" if low in ("code_image", "code_av") else "fid"
                    for row in (step.now, step.values):
                        fid = integer_of((row or {}).get(column))
                        if fid is not None:
                            result.files_touched.add(fid)
        result.suggestions_on_removed_files += \
            change.suggestions_on_removed_files
        session, items = _marks_of(change.record)
        mark = SESSION_MARKS.get(change.tool)
        if mark in ("approved", "proposals") and session:
            result.marks.append((mark, session, tuple(items)))
        elif mark == "applied":
            for step in change.put_back:
                if step.table.lower() != "code_text" or not step.values:
                    continue
                v = step.values
                result.marks.append((
                    "applied", integer_of(v.get("fid")),
                    integer_of(v.get("cid")), integer_of(v.get("pos0")),
                    integer_of(v.get("pos1")), step.key,
                    text_of(v.get("owner"))))


# ---------------------------------------------------------------------------
# The write, under SQLite's write lock, in the write's own transaction
# ---------------------------------------------------------------------------

class WriteCheckFailed(Exception):
    """A row the undo wrote does not read back as planned: the write is
    rolled back, as a SQLite error rolls it back."""


def _rank(table: str) -> int:
    low = table.lower()
    return TABLE_ORDER.index(low) if low in TABLE_ORDER else len(TABLE_ORDER)


def _where(step: Step, start: int) -> Tuple[str, List[Any]]:
    """The row's place: its integer key, its unique value, or nothing for
    the one-row table."""
    if step.key_kind == "integer":
        return rf" WHERE {_quoted(step.key_column)} = ?{start}", [step.key]
    if step.key_kind == "digest":
        value = (step.now or step.values or {}).get(step.key_column, NULL)
        clause, param = _equal_sql(step.key_column, value, start)
        return " WHERE " + clause, [param]
    return "", []


def _settings(columns: Sequence[str]) -> str:
    """`column = <value>, ...` for an UPDATE, two parameters a value."""
    return ", ".join(f"{_quoted(column)} = {_write_sql(2 * i + 1)}"
                     for i, column in enumerate(columns))


def _bound(step: Step) -> List[Any]:
    """A step's values as `_write_sql`'s parameters, in its columns' order."""
    params: List[Any] = []
    for column in step.columns:
        params.extend(bind(step.values[column]))
    return params


def _grouped(steps: Iterable[Step]) -> Dict[Tuple[str, Tuple[str, ...]],
                                            List[Step]]:
    """Steps by table and columns, the order kept within each."""
    groups: Dict[Tuple[str, Tuple[str, ...]], List[Step]] = {}
    for step in steps:
        groups.setdefault((step.table, step.columns), []).append(step)
    return groups


def write(conn: sqlite3.Connection, plan_: Plan, secret: str) -> None:
    """Put the plan's rows back, change by change, newest first: the rows
    each change added removed, children first; the rows it changed set
    back; the rows it removed put back with their ids, parents first.
    Then every row written is read back and compared with the plan, and
    any difference raises WriteCheckFailed, before the commit."""
    for change in plan_.changes:
        removed = _grouped(change.removed)
        for (table, _), steps in sorted(removed.items(),
                                        key=lambda g: -_rank(g[0][0])):
            for kind_steps in _by_key_kind(steps):
                where, _ = _where(kind_steps[0], 1)
                conn.executemany(
                    f"DELETE FROM main.{_quoted(table)}{where}",
                    [_where(step, 1)[1] for step in kind_steps])
        for (table, columns), steps in _grouped(change.set_back).items():
            for kind_steps in _by_key_kind(steps):
                start = 2 * len(columns) + 1
                where, _ = _where(kind_steps[0], start)
                conn.executemany(
                    f"UPDATE main.{_quoted(table)} SET {_settings(columns)}"
                    f"{where}",
                    [_bound(step) + _where(step, start)[1]
                     for step in kind_steps])
        put_back = _grouped(change.put_back)
        for (table, columns), steps in sorted(put_back.items(),
                                              key=lambda g: _rank(g[0][0])):
            names = ", ".join(_quoted(c) for c in columns)
            marks = ", ".join(_write_sql(2 * i + 1)
                              for i in range(len(columns)))
            conn.executemany(
                f"INSERT INTO main.{_quoted(table)} ({names}) "
                f"VALUES ({marks})", [_bound(step) for step in steps])
    _check_written(conn, plan_, secret)


def _by_key_kind(steps: List[Step]) -> List[List[Step]]:
    """Steps of one table split so that each statement's place takes one
    form: a unique value's place binds a text, a number or bytes."""
    groups: Dict[str, List[Step]] = {}
    for step in steps:
        if step.key_kind == "digest":
            value = (step.now or step.values or {}).get(step.key_column, NULL)
            form = "text" if value.kind == "text" else "other"
        else:
            form = step.key_kind
        groups.setdefault(form, []).append(step)
    return list(groups.values())


def _check_written(conn: sqlite3.Connection, plan_: Plan, secret: str) -> None:
    source = Source(conn, Digests(secret))
    wanted: Dict[str, List[Tuple[Any, Tuple[str, ...]]]] = {}
    kinds: Dict[str, Tuple[Optional[str], str]] = {}
    for change in plan_.changes:
        for step in change.removed + change.put_back + change.set_back:
            kinds[step.table.lower()] = (step.key_column, step.key_kind)
    for (low, key), (actual, columns) in plan_.checked.items():
        wanted.setdefault(actual, []).append((key, columns))
    wrong = 0
    for actual, entries in wanted.items():
        key_column, key_kind = kinds[actual.lower()]
        columns_read = sorted({c for _, columns in entries for c in columns})
        got = source.rows(actual, key_column, key_kind,
                          [key for key, _ in entries], only=columns_read)
        for key, columns in entries:
            expected = plan_.overlay.get(actual.lower(), {}).get(key)
            row = got.get(key)
            if expected is None:
                wrong += row is not None
            elif row is None or any(
                    (row.get(c, NULL).kind, row.get(c, NULL).raw)
                    != (expected[c].kind, expected[c].raw) for c in columns):
                wrong += 1
    if wrong:
        raise WriteCheckFailed(wrong)
