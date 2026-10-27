# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the removals of arguments, part two: attributes on journal
entries, and the rename back recognised from the project's backups, go,
as announced in 0.14 (DESIGN_0151_removals-arguments.md, "How it is
checked", items 7 to 11).

7. create_attribute_type with applies_to journal, and set_attribute with
   target_type journal, are refused with their sentence as their first
   check: before the private-marker check, the AI coder name, the lock
   and any backup; journal attributes made by QualCoder are still listed.
8. A text with no stored file renamed away from the name of its copy in
   the documents folder, then back, meets the documents folder's
   refusal, which names restore_backup; nothing is written.
9. No rename opens a backup's database, whether it is accepted, refused
   by the documents folder or refused by the ending rule.
10. An ending the name of the file's stored file has is still put back.
11. The two deprecation constants and the backup reader are gone,
    NOTICE's entry 47 is withdrawn, and no shipped text says that
    rename_file reads backups or that Exegete sets attributes on journal
    entries; the CHANGELOG and the refusal's own sentence aside.
"""

import json
import re
import shutil
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

import exegete.server as server
from exegete import database

from test_v014_server_wide import host_json, host_session, served_texts
from test_v0151_one_backup import call, snapshot

REPO = Path(__file__).resolve().parent.parent
SENTENCE = server.JOURNAL_ATTRIBUTES_REMOVED
DOCUMENTS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
             "SUPPORT.md", "QUICKSTART.md", "AI_CODING_GUIDE.md",
             "AI_CODING_WORKFLOW.md", "PROJECT_SELECTION_GUIDE.md",
             "CLAUDE.md", "packaging/pypi-old-name/README.md")

# What 0.15.0 served, for the put-back the older tests use
DEPRECATED_JOURNAL_ATTRIBUTES_0150 = (
    "Deprecated, removed in v0.15.1: attributes on journal entries, which "
    "Exegete can set but never reads back (QualCoder's Journals window, "
    "for researchers who use it, sets and shows them).")
DEPRECATED_RENAME_BACK_0150 = (
    "Deprecated, removed in v0.15.1: a rename back recognised from the "
    "project's backups (QualCoder's own Rename, if the researcher uses it, "
    "still makes one).")


def _sql(folder, sql, args=()):
    with closing(sqlite3.connect(str(Path(folder) / "data.qda"))) as conn:
        rows = conn.execute(sql, args).fetchall()
        conn.commit()
    return rows


# ---------------------------------------------------------------------------
# 7. Attributes on journal entries are refused first
# ---------------------------------------------------------------------------

JOURNAL_CALLS = (
    ("create_attribute_type", {"name": "Mood", "applies_to": " Journal ",
                               "memo": "public ##### private"}),
    ("create_attribute_type", {"name": "Mood", "applies_to": "journal",
                               "create_backup": False}),
    ("set_attribute", {"target_type": "journal", "target_id": 1,
                       "attribute_name": "Mood", "value": "calm"}),
    ("set_attribute", {"target_type": "JOURNAL", "target_id": 1,
                       "attribute_name": "Mood", "value": "calm",
                       "create_backup": True}),
)


def _refused_first(answer):
    assert isinstance(answer, dict), answer
    assert answer["error"] == SENTENCE, answer
    assert set(answer) <= {"error", "create_backup_ignored"}, answer


def test_journal_attributes_are_refused_before_anything_else(tmp_path):
    """Over the host's path, on a project with no AI coder name yet and
    then with QualCoder 3.8.2's lock file active: each call answers the
    sentence alone, and nothing changes, no backup included."""
    server._apply_toolset("full")

    async def drive(client):
        projects = tmp_path / "projects"
        projects.mkdir()
        made = await call(client, "create_project", {
            "name": "Study", "directory": str(projects),
            "coder_name": "Researcher"})
        folder = Path(made["project_path"])
        answers = []
        before = snapshot(folder)
        # no AI coder name: every other write stops to ask for it
        asked = await call(client, "create_attribute_type", {
            "name": "Age", "applies_to": "case"})
        for name, arguments in JOURNAL_CALLS:
            answers.append(await call(client, name, arguments))
        unasked = snapshot(folder)
        lock = folder / "project_in_use.lock"
        lock.write_text(f"someone\n{time.time()}\n", encoding="utf-8")
        try:
            for name, arguments in JOURNAL_CALLS:
                answers.append(await call(client, name, arguments))
            locked = snapshot(folder)
        finally:
            lock.unlink()
        return before, asked, answers, unasked, locked

    before, asked, answers, unasked, locked = host_session(drive)
    assert "error" in asked and SENTENCE not in json.dumps(asked)
    for answer in answers:
        _refused_first(answer)
    assert before == unasked == locked


def test_journal_attributes_made_elsewhere_stay_listed(setup_server,
                                                       qualcoder_db_path):
    """A journal attribute and its value, as QualCoder writes them, are
    still listed and kept; a refused call leaves them as they were."""
    _sql(qualcoder_db_path,
         "INSERT INTO attribute_type VALUES ('Mood', '2024-01-15', "
         "'TestCoder', 'How the week felt', 'journal', 'character')")
    _sql(qualcoder_db_path,
         "INSERT INTO attribute (name, attr_type, value, id, date, owner) "
         "VALUES ('Mood', 'journal', 'calm', 1, '2024-01-15', 'TestCoder')")
    listed = host_json("list_attribute_types")
    mood = [a for a in listed["attributes"] if a["name"] == "Mood"]
    assert len(mood) == 1 and mood[0]["applies_to"] == "journal", mood
    _refused_first(host_json("set_attribute", {
        "target_type": "journal", "target_id": 1, "attribute_name": "Mood",
        "value": "tense"}))
    assert host_json("list_attribute_types") == listed
    assert _sql(qualcoder_db_path,
                "SELECT value, owner FROM attribute WHERE name = 'Mood'") \
        == [("calm", "TestCoder")]
    # a case or file attribute is set as before
    assert host_json("set_attribute", {
        "target_type": "case", "target_id": 1, "attribute_name": "Age",
        "value": "31"})["success"] is True


# ---------------------------------------------------------------------------
# 8 to 10. The rename back
# ---------------------------------------------------------------------------

@pytest.fixture
def legacy(setup_server, qualcoder_db_path):
    """Entry 5, a text with no stored file, whose copy QualCoder finds
    by its name in the documents folder."""
    project = Path(qualcoder_db_path)
    (project / "documents").mkdir(exist_ok=True)
    (project / "documents" / "legacy.txt").write_text("original")
    _sql(project, "INSERT INTO source (id, name, fulltext, mediapath, memo, "
                  "owner, date) VALUES (5, 'legacy.txt', 'Some text.', "
                  "NULL, '', 'gui_user', '2024-01-15 10:00:00')")
    server.switch_project(server.current_project_path)
    return project


def _rename(file_id, name):
    return host_json("rename_file", {"file_id": file_id, "new_name": name})


def _beside(project):
    """The names beside the project: its backups among them."""
    return sorted(p.name for p in Path(project).parent.iterdir())


def _rows(project):
    return _sql(project, "SELECT id, name, mediapath FROM source "
                         "ORDER BY id")


def test_a_rename_back_meets_the_documents_folders_refusal(legacy):
    away = _rename(5, "legacy2.txt")
    assert away["changed"] is True and "deprecated" not in away
    rows, beside = _rows(legacy), _beside(legacy)
    back = _rename(5, "legacy.txt")
    assert back["error"].startswith(
        "The project's documents folder already holds a file called "
        "'legacy.txt'."), back
    assert "restore_backup" in back["error"]
    assert "rename back" not in back["error"]
    assert "from a backup" not in back["error"]
    assert set(back) <= {"error", "candidates"}
    assert _rows(legacy) == rows and _beside(legacy) == beside
    assert (legacy / "documents" / "legacy.txt").read_text() == "original"


def _spy_connections(monkeypatch):
    seen = []
    real = sqlite3.connect

    def connect(target, *args, **kwargs):
        seen.append(str(target))
        return real(target, *args, **kwargs)
    monkeypatch.setattr(database.sqlite3, "connect", connect)
    return seen


def _backups(project):
    project = Path(project)
    return [p.name for p in project.parent.iterdir()
            if p.is_dir() and p != project and (
                p.name.startswith(f"{project.stem}_backup_")
                or p.name.startswith(f"{project.stem}_BKUP_"))]


def test_no_rename_opens_a_backups_database(legacy, monkeypatch):
    """Every backup that shows the earlier names, Exegete's and
    QualCoder's, is there before each rename, and none is opened."""
    _sql(legacy, "INSERT INTO source (id, name, fulltext, mediapath, memo, "
                 "owner, date) VALUES (6, 'Thomas.Jones', 'Words.', NULL, "
                 "'', 'gui_user', '2024-01-15 10:00:00')")
    server.switch_project(server.current_project_path)
    assert _rename(5, "legacy2.txt")["changed"] is True
    assert _rename(6, "P01 notes")["changed"] is True
    qualcoders = legacy.parent / f"{legacy.stem}_BKUP_20240101_10.qda"
    shutil.copytree(legacy, qualcoders)
    _sql(qualcoders, "UPDATE source SET name = 'legacy.txt' WHERE id = 5")
    _sql(qualcoders, "UPDATE source SET name = 'Thomas.Jones' WHERE id = 6")
    seen = _spy_connections(monkeypatch)
    for file_id, name, outcome in (
            (5, "legacy.txt", "already holds"),          # the documents rule
            (6, "Thomas.Jones", "This text has no stored file"),   # ending
            (1, "P02.txt", None)):                       # accepted
        held = _backups(legacy)
        assert len(held) >= 3, held                      # two ours, one QC's
        del seen[:]
        answer = _rename(file_id, name)
        if outcome is None:
            assert answer["changed"] is True, answer
        else:
            assert outcome in answer["error"], answer
        opened = [target for target in seen
                  if any(backup in target for backup in held)]
        assert not opened, (name, opened)
    # the spy sees a backup's database opened, as the restore's count
    # opens one
    assert database.project_counts(qualcoders, immutable=True)
    assert [target for target in seen if qualcoders.name in target]


@pytest.mark.parametrize("name, mediapath, restored", [
    ("report", "/docs/report.pdf", "report.pdf"),     # a PDF's '.pdf'
    ("notes.pdf", "/docs/notes.docx", "notes.docx"),  # a document's own
])
def test_an_ending_its_stored_file_has_is_put_back(
        setup_server, qualcoder_db_path, name, mediapath, restored):
    _sql(qualcoder_db_path,
         "INSERT INTO source (id, name, fulltext, mediapath, memo, owner, "
         "date) VALUES (5, ?, 'Some text.', ?, '', 'gui_user', "
         "'2024-01-15')", (name, mediapath))
    server.switch_project(server.current_project_path)
    answer = _rename(5, restored)
    assert answer["changed"] is True, answer
    assert "deprecated" not in answer


# ---------------------------------------------------------------------------
# 11. What is gone, and the texts
# ---------------------------------------------------------------------------

def test_the_constants_and_the_backup_reader_are_gone():
    for name in ("DEPRECATED_JOURNAL_ATTRIBUTES", "DEPRECATED_RENAME_BACK",
                 "_is_a_rename_back", "_text_evidence_key"):
        assert not hasattr(server, name), name
    for name in ("earlier_name", "current_text", "TEXT_UNREADABLE",
                 "EARLIER_NAMES_BACKUP_LIMIT"):
        assert not hasattr(database.QualcoderDatabase, name), name
    assert "evidence" not in server._file_rename_precheck.__code__.co_varnames
    assert not hasattr(database, "glob")


def test_the_rename_precheck_reads_no_date(setup_server):
    """The backup reader compared the date; nothing else reads it."""
    rows = server.get_db().file_name_rows()
    assert rows and all(set(row) == {"id", "name", "mediapath",
                                     "av_text_id"} for row in rows)


def test_notice_withdraws_entry_47_in_place():
    from test_licence import NOTICE_WITHDRAWN, _notice_entry_texts
    assert 47 in NOTICE_WITHDRAWN
    texts = _notice_entry_texts()
    assert texts[47].startswith("47. That a file entry's id can be given "
                                "again to a later entry")
    assert "earlier_name" not in " ".join(texts.values())
    assert "_is_a_rename_back" not in " ".join(texts.values())
    notice = " ".join((REPO / "NOTICE").read_text(encoding="utf-8").split())
    assert ("An entry marked withdrawn keeps its number, so that the "
            "entries' references to each other stay true") in notice


# Sentences that say rename_file reads the backups, or that Exegete sets
# attributes on journal entries, in the words 0.15.0 used
READS_BACKUPS = re.compile(
    r"(?i)rename[ -]back|backups? (that )?show(s|ing)? this entry"
    r"|reads? this file's earlier name|recogni[sz]e[sd]? an? rename")
# "in 0.15.0 and earlier", or the refusal's "no longer", say it went
SAYS_GONE = re.compile(
    r"0\.15\.0 and earlier|removed in 0\.15\.1|no longer|not looked for")
SETS_JOURNAL_ATTRIBUTES = re.compile(
    r"(?i)cases, files,? or journals|on a case, file,? or journal\b"
    r"|file ID,? or journal ID|'case', 'file',? or 'journal'"
    r"|on a file or a journal entry|journal attributes are deprecated"
    r"|attributes on journal entries are deprecated"
    r"|can set (them )?but never reads?")


def _flat(text):
    return " ".join(text.split())


def _sentences(text):
    return re.split(r"(?<=[.;!?])\s+(?=[A-Z`*(])", _flat(text))


def _current_claims(text):
    found = []
    for sentence in _sentences(text):
        if SETS_JOURNAL_ATTRIBUTES.search(sentence):
            found.append(sentence)
        elif READS_BACKUPS.search(sentence) and \
                not SAYS_GONE.search(sentence):
            found.append(sentence)
    return found


def _module_strings(path):
    """part one's reader of a module's strings, with this part's
    exceptions: the refusal's own sentence, and the database methods'
    refusal of a domain they do not know, which names 'journal' because
    the methods still take it (the design keeps them), while the tools
    refuse it first."""
    from test_v0151_removed_arguments import _string_constants
    skip = (SENTENCE, "applies_to must be 'case', 'file' or 'journal' "
                      "(QualCoder's real domain set; there is no 'both')",
            "target_type must be 'case', 'file' or 'journal'")
    return [piece for piece in _string_constants(path)
            if piece not in skip]


def test_no_text_says_rename_file_reads_backups_or_journals_take_attributes():
    problems = []
    for mode in ("full", "core"):
        for where, text in served_texts(mode)[0].items():
            problems += [(mode, where, s) for s in _current_claims(text)]
    for path in sorted((REPO / "src" / "exegete").glob("*.py")):
        for piece in _module_strings(path):
            problems += [(path.name, s) for s in _current_claims(piece)]
    for name in DOCUMENTS:
        text = (REPO / name).read_text(encoding="utf-8")
        problems += [(name, s) for s in _current_claims(text)]
    assert not problems, problems


def test_the_readme_and_the_changelog_say_so():
    """README's table names setting an attribute on a journal entry
    among what Exegete does not do; the CHANGELOG records both removals
    and says what to do instead."""
    readme = _flat((REPO / "README.md").read_text(encoding="utf-8"))
    row = [line for line in readme.split("| Cases, attributes, memos, "
                                         "annotations, journal | ")[1:]]
    assert len(row) == 1
    assert "setting an attribute on a journal entry" in \
        row[0][:row[0].index("|", row[0].index("|") + 1)]
    log = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = _flat(log[log.index("## [0.15.1-alpha]"):
                           log.index("## [0.15.0-alpha]")])
    upgrading = unreleased[unreleased.index("### Upgrading from 0.15.0"):]
    upgrading = upgrading[:upgrading.index("### ", 5)]
    assert ("**Attributes on journal entries.** `create_attribute_type` "
            "with `applies_to` `journal`, and `set_attribute` with "
            "`target_type` `journal`, are refused, nothing written.") \
        in upgrading
    assert ("**A rename back is no longer recognised from backups.** "
            "`rename_file` no longer opens the project's backups") \
        in upgrading
    assert "`restore_backup`, which undoes everything done after the " \
           "backup" in upgrading
    removed = unreleased[unreleased.index(
        "### Removed: arguments and behaviours"):]
    removed = removed[:removed.index("### ", 5)]
    assert "**Attributes on journal entries**" in removed
    assert "**A rename back recognised from the project's backups.**" \
        in removed


def test_the_check_finds_what_0150_said():
    for said in (DEPRECATED_JOURNAL_ATTRIBUTES_0150,
                 DEPRECATED_RENAME_BACK_0150,
                 "Define a new attribute for cases, files or journals.",
                 "target_type: 'case', 'file' or 'journal'",
                 "an attribute value it sets on a file or a journal entry",
                 "Exegete recognises a rename back only from a backup that "
                 "shows this entry with that name.",
                 "To recognise a rename back, `rename_file` reads this "
                 "file's earlier name from the project's backups."):
        assert _current_claims(said), said
    for said in (SENTENCE,
                 "in 0.15.0 and earlier, `rename_file` read the names in "
                 "them to recognise a rename back.",
                 "a name the project's backups show is not looked for.",
                 "Define a new attribute for cases or files."):
        assert not _current_claims(said), said


# ---------------------------------------------------------------------------
# The put-back the older tests use
# ---------------------------------------------------------------------------

def before_the_journal_and_rename_back(name, description):
    """`name`'s description as served before this part, on any
    interpreter: for the three tools, the deprecation sentence and the
    texts that said what went put back."""
    from test_v0151_ignored_argument import _swap_lines
    from test_v0151_removed_arguments import _replace_once, _sentence_before
    if name == "create_attribute_type":
        description = _replace_once(
            description, "Define a new attribute for cases or files.",
            "Define a new attribute for cases, files or journals.")
        description = _swap_lines(description, (
            "applies_to: 'case' or 'file' ('journal', QualCoder's third",
            "domain, is refused: Exegete no longer sets attributes",
            "on journal entries)"), (
            "applies_to: 'case', 'file' or 'journal' (QualCoder's real "
            "domain",
            "set; there is no 'both')"), name)
        return _sentence_before(description,
                                DEPRECATED_JOURNAL_ATTRIBUTES_0150)
    if name == "set_attribute":
        description = _replace_once(
            description,
            "Set (or clear) an attribute value on a case or a file.",
            "Set (or clear) an attribute value on a case, file or journal.")
        description = _swap_lines(description, (
            "target_type: 'case' or 'file'",
            "target_id: The case ID or file ID"), (
            "target_type: 'case', 'file' or 'journal'",
            "target_id: The case ID, file ID or journal ID"), name)
        return _sentence_before(description,
                                DEPRECATED_JOURNAL_ATTRIBUTES_0150)
    if name == "rename_file":
        description = _swap_lines(description, (
            "('Thomas.Jones' to 'P01'). An ending the name of its stored "
            "file has",
            "may be put back, except a transcript losing both endings or a "
            "media",
            "file its extension; a name the project's backups show is not "
            "looked",
            "for."), (
            "('Thomas.Jones' to 'P01'). A rename back is not refused: an "
            "ending",
            "the file had before (its stored file's own name, or a project "
            "backup",
            "showing this entry, same id and date) may be restored, except a",
            "transcript losing both endings or a media file its extension; "
            "a text",
            "with no stored file may take back its documents copy under a "
            "name",
            "such a backup shows, with the same text."), name)
        return _sentence_before(description, DEPRECATED_RENAME_BACK_0150,
                                before="The result carries")
    return description
