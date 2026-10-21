# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: the names the list misses, counted by file, never named.

The names list replaces each name exactly as written (whole words, the
same capitals, its words on one line), as QualCoder's import does, so a
form the list does not hold comes into the stored text unsaid. The
import's preview and its answer now count, by file and never by name,
the places where a listed name may still show: pseudonymise_source's
wide reading (other capitals, other characters, a name joined or split
differently, inside a longer word, put back by a pseudonym) and first
names alone; or say that a file was not checked, and why.

Pinned here: the first word and its count; the counts through the tool,
preview and import alike, over the text as stored; that no name reaches
an answer or a log; the allowance's four rules; the catch; the guard;
the note and the line; and that the import counts after its commit,
outside the project's lock file and SQLite's write lock.
"""

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures as fx  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import doc_import, doc_readers, import_paths  # noqa: E402
from exegete import import_words as words  # noqa: E402
from exegete import pseudonymise as pseudo  # noqa: E402
from exegete.database import QUALCODER_LOCK_FILENAME  # noqa: E402

LIST = [("Quorvin Ashdale", "Participant Q")]
FORMS = ("QUORVIN ASHDALE spoke.\nThen Quorvin\nAshdale left.\n"
         "Quorvin said so.\nQuorvin Ashdales came.\n"
         "Quorvin Ashdale agreed.\n")
COUNTED = {"places": 4, "other_capitals": 1,
           "joined_or_split_differently": 1, "first_name_alone": 1,
           "inside_a_longer_word": 1}
# The safety sentence the note and the line both carry: the fact itself
NO_TOOL = ("A name broken by a line break, a tab or an invisible character "
           "cannot be a line, and no Exegete tool replaces it")


def _compiled(pairs):
    return pseudo.Compiled(pseudo.validate_mapping(
        [{"original": o, "pseudonym": p} for o, p in pairs]))


def _alone(pairs, text):
    return pseudo.FirstNamesAlone(_compiled(pairs)).count(text)["count"]


# ---------------------------------------------------------------------------
# The first word and its count
# ---------------------------------------------------------------------------

class TestTheFirstWord:

    @pytest.mark.parametrize("text, count", [
        ("Jane said", 1), ("Jane's", 1), ("JANE", 1), ("jane", 0),
        ("JANE DOE", 0), ("Jane DOE", 0), ("Jane\nDoe", 0),
        ("Jane Does", 0), ("Janes", 0), ("Jane\r\nDoe", 0)])
    def test_a_first_name_alone_is_counted_once(self, text, count):
        """The full name in any form is the wide reading's, never this
        count's (breaks: the lookahead removed; the capital rule)."""
        assert _alone([("Jane Doe", "Participant A")], text) == count

    @pytest.mark.parametrize("name, word", [
        ("Jane Doe", "Jane"), ("Mary-Jane O'Neil", "Mary-Jane"),
        ("(Jane) Doe", "Jane"), ("de la Doe", None), ("J Doe", None),
        ("Jane", None), ("Jane ...", None), ("van Gogh", None),
        ("张 伟", None)])
    def test_the_first_word_of_a_name(self, name, word):
        """Breaks: the capital rule; the length rule (MIN_ORIGINAL_CHARS,
        2); a name of one word."""
        assert pseudo.MIN_ORIGINAL_CHARS == 2
        assert pseudo.first_word(name) == word

    def test_a_first_word_that_is_a_listed_form_is_left_to_the_wide_reading(
            self):
        pairs = [("Jane Doe", "Participant A"), ("JANE", "Participant J")]
        assert pseudo.FirstNamesAlone(_compiled(pairs)).pattern is None
        assert _alone(pairs, "Jane said.") == 0

    def test_the_rest_is_read_as_the_reader_reads_it(self):
        """A curly apostrophe where the list has a straight one: counted
        once, by the wide reading (break: the lookahead built from the
        literal rest)."""
        pairs = [("Mary-Jane O'Neil", "Participant M")]
        text = "Mary-Jane O’Neil said."
        assert _alone(pairs, text) == 0
        found = pseudo.names_left_in_text(_compiled(pairs), text, False, True)
        assert found["entries"][0]["joined_differently"] == 1

    def test_first_words_alike_are_one_group(self):
        """Break: the first words not grouped, which counts "Jane" of
        "Jane Smith" against "Jane Doe" alone."""
        pairs = [("Jane Doe", "Participant A"), ("JANE SMITH", "Participant B")]
        assert _alone(pairs, "Jane Smith spoke.") == 0
        assert _alone(pairs, "Jane Doe spoke.") == 0
        found = pseudo.names_left_in_text(_compiled(pairs), "Jane Smith spoke.",
                                          False, True)
        assert found["occurrences"]["wide"] == 1

    def test_a_longer_first_word_refused_is_not_counted_shorter(self):
        pairs = [("Mary-Jane O'Neil", "Participant M"),
                 ("Mary Smith", "Participant S")]
        assert _alone(pairs, "MARY-JANE O'NEIL said.") == 0
        assert _alone(pairs, "Mary-Jane said.") == 1
        assert _alone(pairs, "Mary said.") == 1

    def test_the_count_stops_at_its_matches(self):
        alone = pseudo.FirstNamesAlone(_compiled([("Jane Doe", "P A1")]))
        assert alone.count("Jane, Jane, Jane, Jane.", max_matches=2) == {
            "count": 2, "matches": 3, "stopped": True}
        assert alone.work("x" * 10) == 10 * (
            alone.units + pseudo.RESIDUE_WORK_PER_CHARACTER)


# ---------------------------------------------------------------------------
# Through import_documents, preview then import
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _names_list(project, pairs=LIST):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in pairs]),
        encoding="utf-8")


def _stored(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%'").fetchall())
    finally:
        con.close()


def _folder(tmp_path, files):
    folder = tmp_path / "Interviews"
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        if isinstance(content, str):
            (folder / name).write_bytes(content.encode("utf-8"))
        else:
            (folder / name).write_bytes(content)
    return folder


def _both(folder, **kwargs):
    preview = _call(paths=[str(folder)], **kwargs)
    assert "preview_token" in preview, preview
    done = _call(paths=[str(folder)], preview_token=preview["preview_token"],
                 **kwargs)
    assert done.get("success") is True, done
    return preview, done


def _entries(answer):
    return {(f.get("name") or f["file"]): f for f in answer["files"]}


def test_the_forms_the_list_misses_are_counted_in_both_answers(project,
                                                               tmp_path):
    """Breaks: counted before the replacement (places 5); a kind summed
    from the wrong key; counted in the preview only; the wide reading used
    to rewrite."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": FORMS})
    preview, done = _both(folder)
    for answer in (preview, done):
        entry = _entries(answer)["P01.txt"]
        assert entry["names_replaced"] == 1
        assert entry["listed_names_left"] == COUNTED
        assert words.say(
            words.WARNINGS, "listed_names_left", places="4 places",
            kinds="other capitals 1, joined or split differently 1, inside "
                  "a longer word 1, a first name alone 1"
        ) in entry["for_information"]
    assert done["names_replaced"] == 1
    assert _stored(project)["P01.txt"] == FORMS.replace(
        "Quorvin Ashdale agreed", "Participant Q agreed")


def test_a_name_over_a_line_break_and_what_no_tool_replaces(project,
                                                            tmp_path):
    _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": "Then Quorvin\nAshdale left.\n"})
    preview, done = _both(folder)
    for answer in (preview, done):
        assert _entries(answer)["P01.txt"]["listed_names_left"] == {
            "places": 1, "joined_or_split_differently": 1}
    assert NO_TOOL in preview["listed_names_left_note"]
    assert NO_TOOL in words.LISTED_NAMES_LEFT_NOTE
    assert server.IMPORT_DONE_LINES["listed_names_left"] in \
        done["for_the_researcher"]
    assert NO_TOOL in server.IMPORT_DONE_LINES["listed_names_left"]


def test_a_name_replaced_whole_leaves_no_field(project, tmp_path):
    """Break: the rewrite's boundary changed."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": "Quorvin Ashdale's dog.\n"})
    preview, done = _both(folder)
    for answer in (preview, done):
        entry = _entries(answer)["P01.txt"]
        assert entry["names_replaced"] == 1
        assert "listed_names_left" not in entry
        assert "listed_names_left_note" not in answer
    assert _stored(project)["P01.txt"] == "Participant Q's dog.\n"
    assert server.IMPORT_DONE_LINES["listed_names_left"] not in \
        done["for_the_researcher"]


def test_the_notes_markers_are_taken_out_before_counting(project, tmp_path):
    """A comment on the first name alone leaves its marker inside the
    name (break: markers left in, which counts the first name alone and
    not the capitals)."""
    _names_list(project)
    _r = fx._r
    word = fx.word(
        "<w:p>" + _r("P1: My neighbour ") + '<w:commentRangeStart w:id="0"/>'
        + _r("Quorvin") + '<w:commentRangeEnd w:id="0"/><w:r>'
        '<w:commentReference w:id="0"/></w:r>' + _r(" ASHDALE drove me.")
        + "</w:p>",
        {"word/comments.xml": fx._part(
            "comments", '<w:comment w:id="0" w:author="Ann"><w:p>'
            + _r("Check.") + "</w:p></w:comment>")})
    folder = _folder(tmp_path, {"P01.docx": word})
    preview, done = _both(folder)
    assert "Quorvin[Comment 1] ASHDALE" in _stored(project)["P01.docx"]
    for answer in (preview, done):
        assert _entries(answer)["P01.docx"]["listed_names_left"] == {
            "places": 1, "other_capitals": 1}


def test_a_pseudonym_holding_the_first_name(project, tmp_path):
    """Counted in the text as stored (break: counted before the
    replacement)."""
    _names_list(project, [("Quorvin Ashdale", "Quorvin A.")])
    folder = _folder(tmp_path, {"P01.txt": "Quorvin Ashdale said.\n"})
    preview, done = _both(folder)
    for answer in (preview, done):
        assert _entries(answer)["P01.txt"]["listed_names_left"] == {
            "places": 1, "first_name_alone": 1}


def _pdf(text):
    def build(doc, pymupdf):
        page = doc.new_page()
        page.insert_text((72, 72), text)
    return fx._pdf(build)


needs_pdf = pytest.mark.skipif(not fx.optional_part_installed(),
                               reason="the optional part is not installed")


@needs_pdf
def test_a_pdf_with_a_name_in_capitals_comes_in_counted(project, tmp_path):
    """Breaks: a PDF held on the wide reading; PDFs not counted."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.pdf": _pdf("QUORVIN ASHDALE spoke.")})
    preview, done = _both(folder)
    for answer in (preview, done):
        entry = _entries(answer)["P01.pdf"]
        assert entry["listed_names_left"] == {"places": 1,
                                              "other_capitals": 1}
        assert "listed_names_kept" not in entry


@needs_pdf
def test_a_pdfs_names_as_listed_are_not_places(project, tmp_path):
    """The whole words of a PDF let in on the researcher's word are
    listed_names_kept's (break: whole_word_in_a_file_not_rewritten kept,
    places 1)."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.pdf": _pdf("Quorvin Ashdale spoke.")})
    preview, done = _both(folder, import_pdfs_with_listed_names=True)
    for answer in (preview, done):
        entry = _entries(answer)["P01.pdf"]
        assert entry["listed_names_kept"] == 1
        assert "listed_names_left" not in entry


def test_no_name_reaches_an_answer_or_a_log(project, tmp_path, caplog):
    """Break: a row of names_left_in_text, which carries the listed name,
    passed into the answer."""
    _names_list(project)
    folder = _folder(tmp_path, {"notes_q.txt": FORMS,
                                "P02.txt": "Quorvin said.\n"})
    with caplog.at_level(logging.DEBUG):
        preview, done = _both(folder)
    shown = (json.dumps(preview, ensure_ascii=False)
             + json.dumps(done, ensure_ascii=False) + caplog.text).casefold()
    assert _entries(done)["notes_q.txt"]["listed_names_left"] == COUNTED
    for name in ("quorvin", "ashdale"):
        assert name not in shown, name


@pytest.mark.parametrize("state", ["none", "empty", "off"])
def test_no_count_without_a_list_to_apply(project, tmp_path, state):
    """Break: the guard removed, which marks every file not checked."""
    if state == "empty":
        (project / "pseudonyms.json").write_text("[]", encoding="utf-8")
    elif state == "off":
        _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": FORMS})
    preview, done = _both(folder,
                          apply_project_pseudonyms=state != "off")
    for answer in (preview, done):
        assert "listed_names_left" not in _entries(answer)["P01.txt"]
        assert "listed_names_left_note" not in answer
    assert server.IMPORT_DONE_LINES["listed_names_left"] not in \
        done["for_the_researcher"]


def test_the_note_and_the_line_come_once_with_any_count(project, tmp_path,
                                                        monkeypatch):
    """Once in a preview whose files carry any of the warnings, the
    import's line likewise, and neither without (break: the condition
    removed)."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": "Quorvin said.\n",
                                "P02.txt": "Quorvin said.\n",
                                "P03.txt": "Nobody here.\n"})
    preview, done = _both(folder)
    assert preview["listed_names_left_note"] == words.LISTED_NAMES_LEFT_NOTE
    assert list(preview).index("listed_names_left_note") == \
        list(preview).index("names_list") + 1
    assert done["for_the_researcher"].count(
        server.IMPORT_DONE_LINES["listed_names_left"]) == 1
    assert "listed_names_left" not in _entries(done)["P03.txt"]
    # Not checked is a warning of the count too
    folder = _folder(tmp_path / "two", {"P04.txt": "Nobody here.\n",
                                        "P05.txt": "Nobody either.\n"})
    monkeypatch.setattr(doc_import, "NAMES_LEFT_MATCHES", 0)
    preview, done = _both(folder)
    assert "listed_names_left_note" in preview
    assert server.IMPORT_DONE_LINES["listed_names_left"] in \
        done["for_the_researcher"]


# ---------------------------------------------------------------------------
# The allowance, each call, under pseudonymise_source's four rules
# ---------------------------------------------------------------------------

def _item(order, text):
    item = doc_import.Item(order=order, given=order,
                           path=Path(f"P{order}.txt"),
                           disk_name=f"P{order}.txt", kind=doc_readers.TEXT,
                           position=doc_import.ordinal(order + 1))
    item.text, item.read, item.name = text, {"notes": []}, f"P{order}.txt"
    return item


def _count(*texts, pairs=LIST):
    ctx = doc_import.Context(project_folder=Path("."), source_names={},
                             documents_listing=[], refused_places=[],
                             compiled=_compiled(pairs))
    items = [_item(order, text) for order, text in enumerate(texts)]
    doc_import.count_names_left(items, ctx)
    return items


def _work(text, pairs=LIST):
    compiled = _compiled(pairs)
    return (pseudo.residue_work(compiled, text)
            + pseudo.FirstNamesAlone(compiled).work(text))


def _said(item, code, **numbers):
    return words.say(words.WARNINGS, code, **numbers) in [
        text for _group, text in item.warnings]


def test_the_allowance_is_the_names_left_counts(monkeypatch):
    assert doc_import.NAMES_LEFT_WORK == pseudo.MAX_RESIDUE_SCAN_WORK
    assert doc_import.NAMES_LEFT_MATCHES == pseudo.MAX_RESIDUE_SCAN_MATCHES


def test_a_file_past_what_is_left_is_not_checked_never_clean(monkeypatch):
    """Break: a file not checked read as clean."""
    text = "Quorvin said.\n" * 10
    monkeypatch.setattr(doc_import, "NAMES_LEFT_WORK", 2 * _work(text) - 1)
    first, second, third = _count(text, text, "x")
    assert first.numbers["listed_names_left"] == {
        "places": 10, "first_name_alone": 10}
    for item in (second, third):
        assert item.numbers["listed_names_left"] == {"not_checked": True}
        assert _said(item, "listed_names_left_not_checked")
        assert doc_import.file_entry(item)["listed_names_left"] == {
            "not_checked": True}


def test_a_file_too_large_closes_nothing(monkeypatch):
    """Too large for a list of this size, in a batch of one, and the small
    file after it counted (breaks: given the not-checked words; it closes
    the rest)."""
    big, small = "Quorvin said. " * 100, "Quorvin said."
    assert pseudo.residue_work_at_one_form(big) < _work(big) // 2
    monkeypatch.setattr(doc_import, "NAMES_LEFT_WORK", _work(big) // 2)
    for batch in ((big,), (big, small)):
        items = _count(*batch)
        assert items[0].numbers["listed_names_left"] == {
            "too_large_to_check": True}
        assert _said(items[0], "listed_names_left_too_large")
        assert not _said(items[0], "listed_names_left_not_checked")
    assert items[1].numbers["listed_names_left"] == {
        "places": 1, "first_name_alone": 1}


def test_a_file_too_large_for_any_list(monkeypatch):
    """Break: residue_work_at_one_form not asked."""
    big = "Quorvin said. " * 100
    monkeypatch.setattr(doc_import, "NAMES_LEFT_WORK",
                        pseudo.residue_work_at_one_form(big) - 1)
    big_item, small_item = _count(big, "Quorvin said.")
    assert _said(big_item, "listed_names_left_too_large_any_list")
    assert not _said(big_item, "listed_names_left_too_large")
    assert small_item.numbers["listed_names_left"]["places"] == 1


@pytest.mark.parametrize("text", ["QUORVIN ASHDALE. " * 10,
                                  "Quorvin said. " * 10])
def test_a_count_stopped_part_way_says_at_least(monkeypatch, text):
    """In the wide reading or in the first names alone (break: a stopped
    count dropped)."""
    monkeypatch.setattr(doc_import, "NAMES_LEFT_MATCHES", 3)
    item, after = _count(text, "Quorvin said.")
    least = item.numbers["listed_names_left"]["at_least"]
    assert 1 <= least <= 10
    assert _said(item, "listed_names_left_at_least",
                 places=words.places_phrase(least))
    assert after.numbers["listed_names_left"] == {"not_checked": True}


def test_the_words_for_the_counts():
    assert words.places_phrase(1) == "1 place"
    assert words.places_phrase(4) == "4 places"
    assert words.kinds_phrase({"first_name_alone": 2, "other_capitals": 1,
                               "other": 0}) == (
        "other capitals 1, a first name alone 2")
    for code in doc_import.NAMES_LEFT_CODES:
        assert words.WARNINGS[code][0] == "information"


# ---------------------------------------------------------------------------
# The import counts after its commit, outside both locks, and never fails
# ---------------------------------------------------------------------------

def _backups(project):
    return sorted(p.name for p in project.parent.iterdir()
                  if p.name.startswith(f"{project.stem}_backup_"))


def _raising_at_the_import(monkeypatch, on_call):
    """names_left_in_text raises at its `on_call`th call of the import,
    with a listed name in the exception's words."""
    real = pseudo.names_left_in_text
    calls = []

    def names_left_in_text(*args, **kwargs):
        calls.append(True)
        if len(calls) == on_call:
            raise RuntimeError("Quorvin Ashdale")
        return real(*args, **kwargs)
    monkeypatch.setattr(pseudo, "names_left_in_text", names_left_in_text)
    return calls


def test_a_count_that_raises_leaves_the_import_whole(project, tmp_path,
                                                     monkeypatch, caplog):
    """That file and the later ones not checked, the answer whole, and the
    log naming the exception's class alone (break: the catch removed)."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": "Quorvin said.\n",
                                "P02.txt": "QUORVIN ASHDALE said.\n",
                                "P03.txt": "Quorvin said.\n"})
    preview = _call(paths=[str(folder)])
    _raising_at_the_import(monkeypatch, 2)
    with caplog.at_level(logging.DEBUG):
        done = _call(paths=[str(folder)],
                     preview_token=preview["preview_token"])
    assert done["success"] is True, done
    found = _entries(done)
    assert found["P01.txt"]["listed_names_left"] == {
        "places": 1, "first_name_alone": 1}
    for name in ("P02.txt", "P03.txt"):
        assert found[name]["listed_names_left"] == {"not_checked": True}
    assert sorted(_stored(project)) == ["P01.txt", "P02.txt", "P03.txt"]
    assert len(_backups(project)) == 1
    assert "RuntimeError" in caplog.text
    assert "quorvin" not in caplog.text.casefold()


def test_the_import_counts_after_its_commit_outside_both_locks(
        project, tmp_path, monkeypatch):
    """When the import's count runs: the lock file gone, SQLite's write
    lock free (another connection takes it and sees the new rows), the
    backup named and the originals under their own names. Then a count
    that raises changes none of it. Break: the count moved before the
    commit or inside the lock file's block."""
    _names_list(project)
    folder = _folder(tmp_path, {"P01.txt": "Quorvin said.\n",
                                "P02.txt": "QUORVIN ASHDALE said.\n"})
    preview = _call(paths=[str(folder)])
    real = doc_import.count_names_left
    seen = []

    def count_names_left(items, ctx):
        con = sqlite3.connect(str(project / "data.qda"), timeout=0)
        try:
            con.execute("BEGIN IMMEDIATE")
            rows = sorted(r[0] for r in con.execute(
                "SELECT name FROM source WHERE mediapath LIKE '/docs/%'"))
            con.rollback()
        finally:
            con.close()
        documents = sorted(p.name for p in (project / "documents").iterdir())
        seen.append(((project / QUALCODER_LOCK_FILENAME).exists(), rows,
                     documents, _backups(project)))
        return real(items, ctx)
    monkeypatch.setattr(doc_import, "count_names_left", count_names_left)
    _raising_at_the_import(monkeypatch, 1)
    done = _call(paths=[str(folder)], preview_token=preview["preview_token"])
    assert done["success"] is True, done
    assert len(seen) == 1
    lock, rows, documents, backups = seen[0]
    assert lock is False
    assert rows == ["P01.txt", "P02.txt"]
    assert documents == ["P01.txt", "P02.txt"]
    assert len(backups) == 1 and done["backup_path"].endswith(backups[0])
    for entry in done["files"]:
        assert entry["listed_names_left"] == {"not_checked": True}
    assert sorted(p.name for p in (project / "documents").iterdir()) == \
        documents
    assert _backups(project) == backups
    assert sorted(_stored(project)) == rows
