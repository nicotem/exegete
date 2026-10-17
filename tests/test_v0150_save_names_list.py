# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: saving the names list (the files design, piece 4).

Pinned here: save_names_list's preview, which reads the names file and
the project's pseudonyms.json once each and gives counts and line
numbers, never a name; each of its refusals and blocking checks, with
line numbers as a text editor counts them; the two warnings and the
warning for entries a save would remove (a names file older than the
list); the engine's rule table (`pseudonymise.rule_broken`), which
agrees with the engine's own checks and adds the backslash; the guard,
whose every refusal a check meets first; the effect against the list
now; the token, given only with nothing to correct and refused once
anything changed; the save, after a backup and under the lock file, in
QualCoder's format, the longest real name first, the names file never
changed; that no name reaches an answer, a log line or a token; the
texts, the sets, the marks and the documents.
"""

import asyncio
import io
import json
import logging
import os
import re
import stat
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import (names_file, opener, preview_tokens,  # noqa: E402
                     private_files)
from exegete import pseudonymise as pseudo  # noqa: E402
from exegete.names_file import HEADER  # noqa: E402

POSIX = os.name == "posix"
WINDOWS = sys.platform == "win32"
BOM = b"\xef\xbb\xbf"
NAMES_FILE = "Names to replace.txt"

DESCRIPTION = (
    "Check the names file the researcher filled in on their own computer "
    "(see prepare_names_list) and save it as the project's names list, "
    "pseudonyms.json, in QualCoder's format, which import_documents "
    "applies to later imports. "
    "Two calls. Without preview_token: a preview of counts and line "
    "numbers, never a name: lines read, lines it could not read, lines "
    "with an empty side, a real name listed twice, a pseudonym that is "
    "also a listed real name, a line breaking one of Exegete's rules, a "
    "pseudonym that would put a listed name back, and how many entries the "
    "list gains, changes and loses. Show the researcher the preview. When "
    "lines need correcting, they correct them in the file and you preview "
    "again; with nothing to correct, the preview gives a token. Only on "
    "the researcher's word, call again with preview_token. A backup of the "
    "project is made first. Never open or read the file yourself.")
NO_NAMES_FILE = (
    "There is no names file in this project's Exegete folder. Call "
    "prepare_names_list to make one.")
NOT_READABLE = {
    "link": "The names file is a link, which Exegete does not follow, so "
            "it was not read.",
    "not_a_file": "The names file is not an ordinary file, so it was not "
                  "read.",
    "too_large": "The names file is larger than 1 MB, so it was not read.",
}
# Fix round 1: piece 3's sentence ends each refusal and step that asks the
# researcher to act on the file
NEVER_OPEN = (
    "Never open or read the file yourself, even when a file tool could.")
NOT_UTF8 = (
    "The names file is not saved as UTF-8 text. Ask the researcher to save "
    "it again as plain text in UTF-8 (most text editors offer the encoding "
    "when saving a file), then preview again. " + NEVER_OPEN)
EMPTY = (
    "The names file holds no names yet, only notes or blank lines. Ask the "
    "researcher to fill it in and save it, then preview again. "
    + NEVER_OPEN)
UNREADABLE_ADVICE = (
    "Exegete does not replace a names list it cannot read. The researcher "
    "can correct pseudonyms.json in a text editor, or move it out of the "
    "project folder, then preview again.")
RULE_NOT_DESCRIBED = (
    "The list breaks a rule of Exegete's for names lists that this preview "
    "does not describe, so it cannot be saved.")
HINT = ("Show the researcher these counts; call again with preview_token "
        "only on their word.")
SHARED = ("The same pseudonym on more than one line: right for forms of "
          "one person's name, wrong for two people.")
NO_BACKUP = (
    "No backup could be made, so the names list was not saved. The "
    "researcher can check that the disk has free space and that the "
    "project folder can be written to, then preview again.")
NOTE = (
    "The names list is saved as pseudonyms.json. import_documents applies "
    "it to the documents it brings in from now on, unless asked not to; "
    "documents already in the project keep their text, and "
    "pseudonymise_source with use_project_pseudonyms replaces the names in "
    "them, a file at a time. Exegete applies the list in one pass, longest "
    "name first, so nothing it writes is replaced again; QualCoder's text "
    "and transcript imports, for those who use them, apply it one entry at "
    "a time in the file's order, which is why it is saved longest real "
    "name first; there two names that overlap without either containing "
    "the other (Mary Ann and Ann Lee, in Mary Ann Lee) can come out "
    "differently, and a pseudonym that contains a name from the list is "
    "rewritten again. The names file stays as the place to change the "
    "list: edit it, save it, and call save_names_list again.")
# The token refused in the names file's words (fix round 1)
TOKEN_CHANGED = (
    "preview_token did not verify for this save. The likeliest reason is "
    "that the names file or the project's names list changed since the "
    "preview, so the token no longer applies.")
TOKEN_CHANGED_UNDER_THE_LOCK = (
    "The names file or the project's names list changed since the "
    "preview, so the token no longer applies. Call save_names_list "
    "without preview_token for a fresh preview, show the researcher what "
    "it says, then save on their word. Nothing was changed.")
# The design's table, word for word
RULES = {
    "name_too_short": "the real name is shorter than 2 characters",
    "name_too_long": "the real name is longer than 200 characters",
    "pseudonym_too_short": "the pseudonym is shorter than 3 characters",
    "pseudonym_too_long": "the pseudonym is longer than 200 characters",
    "hidden_characters": (
        "a side holds an invisible control or direction character, a line "
        "or paragraph separator, or five # in a row"),
    "pseudonym_rare_characters": (
        "the pseudonym holds an emoji or another character Exegete keeps "
        "out of the text it writes"),
    "pseudonym_backslash": (
        "the pseudonym holds a backslash, which a program applying the "
        "list with Python's re.sub, QualCoder's import among them, reads "
        "as an instruction rather than a letter"),
}
LOG_LINE = "save_names_list saved the project's names list (%d entries)."
BLOCKING = ("lines_not_read", "empty_sides", "real_names_listed_twice",
            "pseudonyms_also_real_names", "lines_breaking_a_rule")


def _flat(text):
    return " ".join(text.split())


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _symlink(link: Path, target: Path, folder: bool = False) -> bool:
    try:
        link.symlink_to(target, target_is_directory=folder)
    except (OSError, NotImplementedError):
        return False
    return True


@pytest.fixture
def selected(tmp_path):
    """A project selected the way a researcher selects one, under a path
    with spaces, with its Exegete folder made."""
    from test_v012_pseudonymise_tool import build_project
    from track5_helpers import write_fixture_sidecar
    folder = build_project(tmp_path / "My studies" / "Study two.qda")
    write_fixture_sidecar(str(folder))
    original = (server.db, server.current_project_path)
    answer = json.loads(server.select_project(str(folder)))
    assert answer.get("success") is not False, answer
    private_files.ensure_folder(folder)
    yield folder
    if server.db is not None:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = original


@pytest.fixture
def asked(monkeypatch):
    """Recorders in place of the launchers, accepting every call."""
    calls = []
    monkeypatch.setattr(opener, "_run",
                        lambda argv: calls.append(list(argv)) or 0)
    monkeypatch.setattr(opener, "_startfile",
                        lambda path: calls.append(["startfile", path])
                        or True)
    monkeypatch.setattr(opener, "_which", lambda name: f"/usr/bin/{name}")
    for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    return calls


def _names(folder):
    return folder / "Exegete" / NAMES_FILE


def _write_names(folder, *lines, header=True, ending="\n", mark=False):
    """The names file as a text editor saves it: the five lines of
    instructions (unless `header` is false), then `lines`."""
    text = (HEADER if header else "") + "".join(
        line + "\n" for line in lines)
    raw = text.replace("\n", ending).encode("utf-8")
    _names(folder).write_bytes((BOM if mark else b"") + raw)
    return raw


def _write_list(folder, entries, **extra):
    """pseudonyms.json as QualCoder's dialog writes it: the entries in the
    order given, `json.dump(..., indent=2)`."""
    data = [{"original": o, "pseudonym": p} for o, p in entries]
    for index, keys in extra.items():
        data[int(index.lstrip("e"))].update(keys)
    (folder / "pseudonyms.json").write_text(json.dumps(data, indent=2),
                                            encoding="utf-8")


def _list_bytes(folder):
    return (folder / "pseudonyms.json").read_bytes()


_SEPARATORS = re.compile(r"=>|->|→|=|\t|,")
_JSON_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _names_in_reach():
    """Every real name and pseudonym a call could reach: each string in
    pseudonyms.json (read as text, so a list the reader refuses counts
    too), and each side of every line of the names file (read as UTF-8,
    or failing that cp1252), less those of fewer than three characters
    and any that Exegete's own words for this tool hold."""
    if server.current_project_path is None:
        return set()
    folder = Path(server._current_project_folder())
    found = set()
    try:
        text = (folder / "pseudonyms.json").read_text(encoding="utf-8")
    except (OSError, ValueError):
        text = ""
    for literal in _JSON_STRING.findall(text):
        try:
            found.add(json.loads(f'"{literal}"'))
        except ValueError:
            found.add(literal)
    try:
        info = os.stat(_names(folder))
        raw = _names(folder).read_bytes() if stat.S_ISREG(info.st_mode) \
            and info.st_size <= private_files.MAX_READ else b""
    except OSError:
        raw = b""
    try:
        lines = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        lines = raw.decode("cp1252", errors="replace")
    for line in re.split(r"\r\n|\r|\n", lines):
        if not line.lstrip(" \t").startswith("#"):
            found.update(side.strip() for side in _SEPARATORS.split(line))
    own_words = " ".join(
        value for key, value in vars(server).items()
        if isinstance(value, str) and key.startswith(
            ("SAVE_NAMES_LIST", "NAMES_FILE", "NO_NAMES", "NAMES_LIST",
             "RULE_NOT", "NO_BACKUP", "TOKEN_ERROR")))
    own_words += " ".join(pseudo.RULE_WORDS.values())
    own_words += " ".join(server.TOKEN_ERROR_TEXTS.values())
    return {name for name in found if len(name.strip()) >= 3
            and name not in ("original", "pseudonym")
            and name not in own_words}


def _strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _save(token=None, **kwargs):
    """save_names_list's answer, parsed, after proving on every call that
    no real name or pseudonym within its reach is in it, as written or
    escaped."""
    before = _names_in_reach()
    raw = server.save_names_list(**({"preview_token": token} if token
                                    else {}), **kwargs)
    answer = json.loads(raw)
    names = before | _names_in_reach()
    said = "\n".join(_strings(answer))
    for name in names:
        for form in {name, name.strip()}:
            assert form not in said, form
            assert json.dumps(form)[1:-1] not in raw, form
    return answer


@pytest.fixture(autouse=True)
def _no_name_in_any_log(request, caplog, capsys, monkeypatch):
    """Fix round 1: every test in this file, its failure paths included,
    reads the log at DEBUG (caplog, a root handler of its own, and the
    captured standard error and output) and fails at its end if a name
    within reach of any call of save_names_list or prepare_names_list
    (taken before and after each call, and at the end) is in it, as
    written or escaped."""
    if "selected" in request.fixturenames:
        # set up first, so that the project is still selected at the end
        request.getfixturevalue("selected")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    caplog.set_level(logging.DEBUG)
    reach = set()
    for name in ("save_names_list", "prepare_names_list"):
        def wrapped(*args, _real=getattr(server, name), **kwargs):
            reach.update(_names_in_reach())
            try:
                return _real(*args, **kwargs)
            finally:
                reach.update(_names_in_reach())
        monkeypatch.setattr(server, name, wrapped)
    try:
        yield
    finally:
        root.removeHandler(handler)
    reach.update(_names_in_reach())
    printed = capsys.readouterr()
    logs = "\n".join([caplog.text, stream.getvalue(), printed.err,
                      printed.out]
                     + [r.getMessage() for r in caplog.records])
    for name in reach:
        for form in {name, name.strip()}:
            assert form not in logs, form
            assert json.dumps(form)[1:-1] not in logs, form


def _preview(folder):
    """A preview that gives a token; its preview block and the token."""
    answer = _save()
    assert "preview_token" in answer, answer
    return answer


def _saved(folder):
    return json.loads(_list_bytes(folder).decode("ascii"))


# ---------------------------------------------------------------------------
# The rule table
# ---------------------------------------------------------------------------

# Values for the agreement test: each rule's edges, and ordinary names
VALUES = [
    "Jo", "J", "", "Ann", "Mary Ann", "Niccolò", "Smith, Jane", "张伟",
    "P01", "P1", "x" * 200, "x" * 201, "Jane\u0085Doe", "Jane\u2028Doe",
    "Jane\u202eDoe", "Jane\u061cDoe", "Jane\ufeffDoe", "Jane#####Doe",
    "Jane####Doe", "P\U0001f600 1", "P\\1", "C:\\Users", "Jane\rDoe",
    "Jane\tDoe", " Jane", "Jane ", "\u00a0Jane", "Jean-Paul", "O'Brien",
    "Room #4", "Zoë\u200dx", "#Jane", "A = B", "P\udfff1",
    # fix round 1: both an emoji and a backslash, so the order of the two
    # rules is held where the engine's check refuses
    "P\U0001f600\\1",
]


class TestTheRuleTable:

    def test_the_words_are_the_designs(self):
        assert {code: words for code, words in pseudo.RULE_WORDS.items()
                if code != "white_space_at_an_end"} == RULES
        # The engine's own rule a names file's line never meets (its
        # reader strips each side), for an entry kept from the list
        assert pseudo.RULE_WORDS["white_space_at_an_end"] == (
            "a side begins or ends with white space")
        for words in pseudo.RULE_WORDS.values():
            assert "—" not in words

    @pytest.mark.parametrize("value", VALUES)
    def test_it_agrees_with_the_engines_check_of_a_name(self, value):
        rule = pseudo.rule_broken(value, "name")
        try:
            pseudo._check_name(value, 0, "original")
            accepted = True
        except pseudo.MappingError:
            accepted = False
        assert (rule is None) == accepted, (value, rule)
        assert rule in (None, "name_too_short", "name_too_long",
                        "hidden_characters", "white_space_at_an_end")

    @pytest.mark.parametrize("value", VALUES)
    def test_it_agrees_with_the_engines_check_of_a_pseudonym(self, value):
        rule = pseudo.rule_broken(value, "pseudonym")
        try:
            pseudo._check_pseudonym(value, 0, may_echo_names=False)
            accepted = True
        except pseudo.MappingError:
            accepted = False
        # the backslash alone is stricter than the engine
        assert (rule in (None, "pseudonym_backslash")) == accepted, (
            value, rule)

    @pytest.mark.parametrize("value, kind, code", [
        ("J", "name", "name_too_short"),
        ("x" * 201, "name", "name_too_long"),
        ("P1", "pseudonym", "pseudonym_too_short"),
        ("x" * 201, "pseudonym", "pseudonym_too_long"),
        ("Jane\u2029Doe", "name", "hidden_characters"),
        ("P\u200e01", "pseudonym", "hidden_characters"),
        ("P#####1", "pseudonym", "hidden_characters"),
        ("P\U0001f600 1", "pseudonym", "pseudonym_rare_characters"),
        ("P\\1", "pseudonym", "pseudonym_backslash"),
        ("Jane ", "name", "white_space_at_an_end"),
        # the emoji first: the engine refuses it, and the backslash alone
        # is the rule a kept entry may break
        ("P\U0001f600\\1", "pseudonym", "pseudonym_rare_characters"),
    ])
    def test_each_rule_by_a_value_that_breaks_it(self, value, kind, code):
        assert pseudo.rule_broken(value, kind) == code

    def test_a_backslash_in_a_real_name_is_no_rule(self):
        """A real name is looked for, escaped, never written: only the
        pseudonym is the replacement re.sub reads."""
        assert pseudo.rule_broken("C:\\Users", "name") is None

    def test_the_engines_checks_are_unchanged(self):
        """The two checks still accept a backslash (pseudonymise_source
        keeps writing one) and still refuse what they refused."""
        assert pseudo._check_pseudonym("P\\1", 0) == "P\\1"
        with pytest.raises(pseudo.MappingError):
            pseudo._check_name("J", 0, "original")

    def test_an_unknown_kind_is_refused(self):
        with pytest.raises(ValueError):
            pseudo.rule_broken("Jane", "variant")


# ---------------------------------------------------------------------------
# The preview's refusals: each ends it, with a reason, no token, nothing
# changed
# ---------------------------------------------------------------------------

def _refused(answer, reason, text=None):
    assert answer["reason"] == reason, answer
    assert answer["nothing_changed"] is True
    assert "preview_token" not in answer and "preview" not in answer
    if text is not None:
        assert answer["error"] == text
    return answer["error"]


class TestTheRefusals:

    def test_no_project_open(self, monkeypatch):
        monkeypatch.setattr(server, "current_project_path", None)
        monkeypatch.setattr(server, "_adopt_configured_project",
                            lambda: None)
        answer = json.loads(server.save_names_list())
        assert answer == {"error": server._no_project_message()}

    def test_no_names_file(self, selected):
        _refused(_save(), "no_names_file", NO_NAMES_FILE)

    def test_no_exegete_folder(self, selected):
        (selected / "Exegete" / "About this folder.txt").unlink()
        (selected / "Exegete").rmdir()
        _refused(_save(), "no_names_file", NO_NAMES_FILE)
        # a preview makes nothing
        assert not (selected / "Exegete").exists()

    def test_a_link(self, selected, tmp_path):
        target = tmp_path / "elsewhere.txt"
        target.write_text("Quorvin Ashdale = Participant Q\n",
                          encoding="utf-8")
        if not _symlink(_names(selected), target):
            pytest.skip("links cannot be made here")
        _refused(_save(), "names_file_not_readable", NOT_READABLE["link"])

    def test_a_folder_at_the_name(self, selected):
        _names(selected).mkdir()
        _refused(_save(), "names_file_not_readable",
                 NOT_READABLE["not_a_file"])

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFO here")
    def test_a_fifo(self, selected):
        os.mkfifo(_names(selected))         # would hang if it were read
        _refused(_save(), "names_file_not_readable",
                 NOT_READABLE["not_a_file"])

    def test_a_file_past_the_limit(self, selected):
        line = "Quorvin Ashdale = Participant Q\n"
        _names(selected).write_text(
            line * (private_files.MAX_READ // len(line) + 1),
            encoding="utf-8")
        _refused(_save(), "names_file_not_readable",
                 NOT_READABLE["too_large"])

    def test_the_folder_a_link_says_so(self, selected, tmp_path):
        """Where the design was silent: the folder's own refusal, then
        that the names file was not read, rather than the file's words."""
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / NAMES_FILE).write_text("Quorvin Ashdale = P01\n",
                                            encoding="utf-8")
        for entry in (selected / "Exegete").iterdir():
            entry.unlink()
        (selected / "Exegete").rmdir()
        if not _symlink(selected / "Exegete", elsewhere, folder=True):
            pytest.skip("links cannot be made here")
        text = _refused(_save(), "names_file_not_readable")
        assert text.startswith("The project's Exegete folder is a link")
        assert text.endswith(" So the names file was not read.")

    @pytest.mark.parametrize("code, words", [
        ("changed", "The names file changed while Exegete was reading it, "
                    "so it was not read. Preview again to read it as it is "
                    "now."),
        ("unreadable", "The system refused to read the names file, so it "
                       "was not read. The researcher can check that they "
                       "can open it in their text editor; then preview "
                       "again. " + NEVER_OPEN)])
    def test_the_readers_other_refusals(self, selected, monkeypatch, code,
                                        words):
        _write_names(selected, "Quorvin Ashdale = Participant Q")

        def refused(project, name):
            raise private_files.PrivateFilesError(code, "It could not.")
        monkeypatch.setattr(private_files, "read_bytes", refused)
        _refused(_save(), "names_file_not_readable", words)

    def test_not_utf8(self, selected):
        _names(selected).write_bytes(
            (HEADER + "Élodie Marchbank = Participant É\n").encode("cp1252"))
        _refused(_save(), "names_file_not_utf8", NOT_UTF8)

    def test_only_notes_and_blank_lines(self, selected):
        _write_names(selected, "", "# Quorvin Ashdale = Participant Q",
                     "   ", "\t# another note")
        _refused(_save(), "names_file_empty", EMPTY)
        _names(selected).write_bytes(b"")
        _refused(_save(), "names_file_empty", EMPTY)

    def test_lines_not_read_are_not_an_empty_file(self, selected):
        """Where the design was silent: a file with no pair but a line
        that could not be read is not "only notes or blank lines"; the
        preview gives that line's number."""
        _write_names(selected, "Quorvin Ashdale")
        answer = _save()
        assert answer["reason"] == "corrections_needed"
        assert answer["preview"]["lines_not_read"] == {
            "count": 1, "lines": [{"line": 6, "reason": "no separator"}]}

    def test_the_list_unreadable(self, selected):
        _write_names(selected, "Quorvin Ashdale = Participant Q")
        (selected / "pseudonyms.json").write_text(
            '[{"original": "Brisemar Tull", ', encoding="utf-8")
        text = _refused(_save(), "pseudonyms_json_unreadable")
        assert text.startswith("The project's names list (pseudonyms.json")
        assert text.endswith(" " + UNREADABLE_ADVICE)
        (selected / "pseudonyms.json").write_text('{"a": 1}',
                                                  encoding="utf-8")
        assert _refused(_save(), "pseudonyms_json_unreadable").endswith(
            UNREADABLE_ADVICE)

    def test_the_list_a_link(self, selected, tmp_path):
        _write_names(selected, "Quorvin Ashdale = Participant Q")
        target = selected / "kept.json"
        target.write_text("[]", encoding="utf-8")
        if not _symlink(selected / "pseudonyms.json", target):
            pytest.skip("links cannot be made here")
        text = _refused(_save(), "pseudonyms_json_is_a_link")
        assert text == (
            "The names list cannot be saved: pseudonyms.json in the project "
            "folder is a symbolic link, and this tool saves by renaming a "
            "new file into place, which would replace the link and leave "
            "the file it points to as it was. If the researcher wants the "
            "list saved, they can replace the link with the file it points "
            "to, then preview again.")

    @pytest.mark.skipif(not POSIX or os.geteuid() == 0,
                        reason="a mode the system enforces")
    def test_the_list_read_only(self, selected):
        _write_names(selected, "Quorvin Ashdale = Participant Q")
        _write_list(selected, [("Brisemar Tull", "Participant B")])
        os.chmod(selected / "pseudonyms.json", 0o444)
        text = _refused(_save(), "pseudonyms_json_read_only")
        assert text == (
            "The names list cannot be saved: pseudonyms.json in the project "
            "folder is read-only for this account, and Exegete leaves it "
            "so. If the researcher wants the list saved, they can make the "
            "file writable again, then preview again.")

    def test_the_guards_refusal(self, selected, monkeypatch):
        _write_names(selected, "Quorvin Ashdale = Participant Q")

        def refuses(*args, **kwargs):
            raise pseudo.MappingError("mapping entry 0: a rule")
        monkeypatch.setattr(pseudo, "validate_mapping", refuses)
        _refused(_save(), "rule_not_described", RULE_NOT_DESCRIBED)


# ---------------------------------------------------------------------------
# The checks: blocking ones by line number, each alone and with others
# ---------------------------------------------------------------------------

GOOD = "Quorvin Ashdale = Participant Q"


def _blocked(folder):
    answer = _save()
    assert answer["reason"] == "corrections_needed", answer
    assert answer["nothing_changed"] is True
    assert "preview_token" not in answer
    assert "execute_with" not in answer
    assert answer["next_step"].startswith(server.SAVE_NAMES_LIST_CORRECT)
    return answer["preview"], answer


def _only(preview, key):
    """Every other blocking check is clear."""
    for other in BLOCKING:
        if other != key:
            assert preview[other] == {"count": 0, "lines": []}, other
    if key != "too_many_names":
        assert preview["too_many_names"] is False
    if key != "kept_entries_in_conflict":
        assert preview["kept_entries_in_conflict"] == 0


class TestTheBlockingChecks:

    def test_lines_not_read(self, selected):
        # lines 6 to 9: good, no separator, two separators, a tab at the
        # end of an otherwise good line
        _write_names(selected, GOOD, "Quorvin", "A = B = C",
                     "Brisemar Tull = Participant B\t")
        preview, answer = _blocked(selected)
        assert preview["lines_not_read"] == {"count": 3, "lines": [
            {"line": 7, "reason": "no separator"},
            {"line": 8, "reason": "more than one separator"},
            {"line": 9, "reason": "more than one separator"}]}
        assert preview["lines_read"] == 1
        _only(preview, "lines_not_read")
        assert server.SAVE_NAMES_LIST_NOT_READ in answer["next_step"]

    def test_empty_sides(self, selected):
        _write_names(selected, GOOD, "= Participant Z", "Brisemar Tull =")
        preview, answer = _blocked(selected)
        assert preview["empty_sides"] == {"count": 2, "lines": [7, 8]}
        _only(preview, "empty_sides")
        assert server.SAVE_NAMES_LIST_NOT_READ not in answer["next_step"]

    def test_a_real_name_listed_twice(self, selected):
        _write_names(selected, GOOD, "Brisemar Tull = Participant B",
                     "Quorvin Ashdale = Participant R")
        preview, _ = _blocked(selected)
        assert preview["real_names_listed_twice"] == {"count": 2,
                                                      "lines": [6, 8]}
        _only(preview, "real_names_listed_twice")

    def test_twice_means_exactly(self, selected):
        """The same real name in another letter case is another name, as
        the engine's exact mode and QualCoder's dialog compare."""
        _write_names(selected, GOOD, "quorvin ashdale = Participant R")
        answer = _preview(selected)
        assert answer["preview"]["real_names_listed_twice"]["count"] == 0

    def test_a_pseudonym_that_is_a_real_name(self, selected):
        _write_names(selected, GOOD, "Brisemar Tull = Quorvin Ashdale")
        preview, _ = _blocked(selected)
        assert preview["pseudonyms_also_real_names"] == {"count": 1,
                                                         "lines": [7]}
        _only(preview, "pseudonyms_also_real_names")

    @pytest.mark.parametrize("line, code", [
        ("Q = Participant Q", "name_too_short"),
        ("x" * 201 + " = Participant Q", "name_too_long"),
        ("Quorvin Ashdale = Q1", "pseudonym_too_short"),
        ("Quorvin Ashdale = " + "x" * 201, "pseudonym_too_long"),
        ("Quorvin\u0085Ashdale = Participant Q", "hidden_characters"),
        ("Quorvin Ashdale = Participant‮Q", "hidden_characters"),
        ("Quorvin Ashdale = Participant ##### Q", "hidden_characters"),
        ("Quorvin Ashdale = Participant \U0001f600",
         "pseudonym_rare_characters"),
        ("Quorvin Ashdale = Participant\\1", "pseudonym_backslash"),
    ])
    def test_each_rule(self, selected, line, code):
        _write_names(selected, "Brisemar Tull = Participant B", line)
        preview, _ = _blocked(selected)
        assert preview["lines_breaking_a_rule"] == {
            "count": 1, "lines": [{"line": 7, "rule": RULES[code]}]}
        _only(preview, "lines_breaking_a_rule")

    def test_both_sides_of_one_line(self, selected):
        _write_names(selected, "Q = Q1")
        preview, _ = _blocked(selected)
        assert preview["lines_breaking_a_rule"] == {"count": 1, "lines": [
            {"line": 6, "rule": RULES["name_too_short"]},
            {"line": 6, "rule": RULES["pseudonym_too_short"]}]}

    def test_too_many_names(self, selected):
        _write_names(selected, *(f"Name{i:04d} = Participant {i:04d}"
                                 for i in range(pseudo.MAX_ENTRIES + 1)))
        preview, answer = _blocked(selected)
        assert preview["too_many_names"] is True
        assert preview["effect"]["entries_after"] == pseudo.MAX_ENTRIES + 1
        _only(preview, "too_many_names")
        assert server.SAVE_NAMES_LIST_TOO_MANY in answer["next_step"]

    def test_five_hundred_are_not_too_many(self, selected):
        _write_names(selected, *(f"Name{i:04d} = Participant {i:04d}"
                                 for i in range(pseudo.MAX_ENTRIES)))
        assert _preview(selected)["preview"]["too_many_names"] is False

    def test_a_name_listed_twice_is_one_entry_towards_too_many(
            self, selected):
        """Fix round 1: too many is counted as entries_after counts the
        entries a save writes; the name listed twice blocks on its own."""
        _write_names(selected, *(f"Name{i:04d} = Participant {i:04d}"
                                 for i in range(pseudo.MAX_ENTRIES)),
                     "Name0000 = Participant 0000")
        preview, answer = _blocked(selected)
        assert preview["effect"]["entries_after"] == pseudo.MAX_ENTRIES
        assert preview["too_many_names"] is False
        assert preview["real_names_listed_twice"] == {
            "count": 2, "lines": [6, 506]}
        assert server.SAVE_NAMES_LIST_TOO_MANY not in answer["next_step"]

    def test_the_kept_entries_count_towards_too_many(self, selected):
        _write_names(selected, *(f"Name{i:04d} = Participant {i:04d}"
                                 for i in range(pseudo.MAX_ENTRIES)))
        _write_list(selected, [("Brisemar = Tull", "Participant B")])
        preview, _ = _blocked(selected)
        assert preview["too_many_names"] is True
        assert preview["effect"]["kept_entries_the_file_cannot_hold"] == 1

    def test_every_problem_at_once(self, selected):
        _write_names(selected, GOOD, "Quorvin", "= Participant Z",
                     "Quorvin Ashdale = Participant R",
                     "Brisemar Tull = Quorvin Ashdale", "Q = Participant S")
        preview, answer = _blocked(selected)
        assert preview["lines_not_read"]["count"] == 1
        assert preview["empty_sides"] == {"count": 1, "lines": [8]}
        assert preview["real_names_listed_twice"]["lines"] == [6, 9]
        assert preview["pseudonyms_also_real_names"]["lines"] == [10]
        assert preview["lines_breaking_a_rule"]["lines"] == [
            {"line": 11, "rule": RULES["name_too_short"]}]

    @pytest.mark.parametrize("kept, line", [
        # its pseudonym is a real name on a line
        (("Brisemar = Tull", "Quorvin Ashdale"), GOOD),
        # its real name (which starts with #, so no line can hold it) is
        # a line's pseudonym
        (("#Participant Q", "Participant B"),
         "Quorvin Ashdale = #Participant Q"),
    ])
    def test_a_kept_entry_in_conflict_with_a_line(self, selected, kept,
                                                  line):
        _write_names(selected, line)
        _write_list(selected, [kept])
        preview, answer = _blocked(selected)
        assert preview["kept_entries_in_conflict"] == 1
        _only(preview, "kept_entries_in_conflict")
        assert server.SAVE_NAMES_LIST_KEPT_CONFLICT in answer["next_step"]
        # fix round 1: the lines the researcher can find, not "those lines"
        assert ("The researcher can change the lines whose names those "
                "entries use, or correct or remove those entries in "
                "pseudonyms.json") in server.SAVE_NAMES_LIST_KEPT_CONFLICT

    @pytest.mark.parametrize("entries", [
        # two kept entries with one real name
        [("Brisemar = Tull", "Participant B"),
         ("Brisemar = Tull", "Participant C")],
        # a kept entry's pseudonym is another kept entry's real name
        [("Brisemar = Tull", "Participant B"),
         ("Ottoline -> Faverdy", "Brisemar = Tull")],
        # kept entries breaking the engine's rules
        [(" Brisemar Tull", "Participant B")],
        [("Brisemar Tull\n", "Participant B")],
        [("#", "Participant B")],
        [("Brisemar = Tull", "P\U0001f600B")],
        [("", "Participant B")],
    ])
    def test_a_kept_entry_the_save_cannot_hold(self, selected, entries):
        """Where the design was silent: kept entries that would make the
        engine refuse the list (repeating one another, chaining, or
        breaking one of its rules) are counted with those in conflict, so
        that the guard never meets a problem the preview did not count."""
        _write_names(selected, GOOD)
        _write_list(selected, entries)
        preview, _ = _blocked(selected)
        assert preview["kept_entries_in_conflict"] >= 1
        _only(preview, "kept_entries_in_conflict")

    def test_a_kept_entry_with_a_backslash_is_kept(self, selected):
        """The backslash rule is for the lines: an entry the list already
        holds, which the file cannot hold, stays as it is (piece 3's open
        point 3), as pseudonymise_source keeps writing one."""
        _write_names(selected, GOOD)
        _write_list(selected, [("Brisemar = Tull", "Participant\\B")])
        answer = _preview(selected)
        preview = answer["preview"]
        assert preview["kept_entries_in_conflict"] == 0
        assert preview["effect"]["kept_entries_the_file_cannot_hold"] == 1
        # fix round 1: counted and said, not kept without a word
        assert preview["kept_entries_with_a_backslash"] == 1
        assert server.SAVE_NAMES_LIST_KEPT_BACKSLASH in answer["warnings"]
        for words in ("(kept_entries_with_a_backslash counts them)",
                      "They are kept as they are",
                      "QualCoder's import among them, reads a backslash as "
                      "an instruction rather than a letter",
                      "change those pseudonyms in pseudonyms.json"):
            assert words in server.SAVE_NAMES_LIST_KEPT_BACKSLASH, words

    def test_a_kept_entry_holding_an_emoji_and_a_backslash(self, selected):
        """Fix round 1: the emoji's rule is met first, so the entry is in
        conflict, never kept for the guard to refuse."""
        _write_names(selected, GOOD)
        _write_list(selected, [("Brisemar = Tull", "P\U0001f600\\B")])
        preview, _ = _blocked(selected)
        assert preview["kept_entries_in_conflict"] == 1
        _only(preview, "kept_entries_in_conflict")

    def test_a_line_wins_over_the_entry_it_names(self, selected):
        _write_names(selected, "Quorvin Ashdale = Participant Q")
        _write_list(selected, [("Quorvin Ashdale", " Participant Z")])
        preview = _preview(selected)["preview"]
        assert preview["kept_entries_in_conflict"] == 0
        assert preview["effect"]["changed"] == 1
        assert preview["effect"]["kept_entries_the_file_cannot_hold"] == 0


class TestLineNumbers:

    def test_the_step_says_how_to_find_a_line_and_never_to_open_it(
            self, selected):
        """Fix round 1: how a line is found by its number, and piece 3's
        sentence on never opening the file, last."""
        _write_names(selected, GOOD, "Quorvin", "Q = Participant S")
        _, answer = _blocked(selected)
        assert answer["next_step"].startswith(server.SAVE_NAMES_LIST_CORRECT)
        assert answer["next_step"].endswith(" " + NEVER_OPEN)
        assert server.PREPARE_NAMES_LIST_NEVER_OPEN == NEVER_OPEN
        assert ("(counted from the first line of the file, the lines of "
                "instructions at the top included; many text editors show a "
                "line's number or can go to one, and in one that shows none, "
                "such as TextEdit, count from the top)") in \
            server.SAVE_NAMES_LIST_CORRECT

    def test_as_a_text_editor_counts_them(self, selected):
        """The five lines of instructions counted; CR LF, CR and LF each
        end a line; a blank line counted; a line separator inside a line
        (U+2028) is no end of line."""
        raw = (HEADER.replace("\n", "\r\n") + GOOD + "\r\n" + "\r\n"
               + "Brisemar Tull = Participant B\r"
               + "Ottoline Faverdy\n" + "= Participant Z\n")
        _names(selected).write_bytes(BOM + raw.encode("utf-8"))
        preview, _ = _blocked(selected)
        assert preview["lines_breaking_a_rule"]["lines"] == [
            {"line": 8, "rule": RULES["hidden_characters"]}]
        assert preview["lines_not_read"]["lines"] == [
            {"line": 9, "reason": "no separator"}]
        assert preview["empty_sides"]["lines"] == [10]

    def test_without_the_five_lines(self, selected):
        _write_names(selected, "Quorvin", GOOD, header=False)
        preview, _ = _blocked(selected)
        assert preview["lines_not_read"]["lines"] == [
            {"line": 1, "reason": "no separator"}]

    def test_each_list_stops_at_200_with_its_count(self, selected):
        _write_names(selected, GOOD, *(f"Name{i:03d}" for i in range(250)),
                     *(f"= P{i:03d}" for i in range(201)))
        preview, _ = _blocked(selected)
        assert preview["lines_not_read"]["count"] == 250
        assert len(preview["lines_not_read"]["lines"]) == 200
        assert preview["lines_not_read"]["lines"][0] == {
            "line": 7, "reason": "no separator"}
        assert preview["empty_sides"]["count"] == 201
        assert preview["empty_sides"]["lines"] == list(range(257, 457))
        assert server.MAX_PREVIEW_LINES == 200

    def test_rules_stop_at_200_and_count_lines(self, selected):
        _write_names(selected,
                     *(f"{chr(0x4E00 + i)} = P\\{i:03d}" for i in range(150)),
                     *(f"Name{i:03d} = R\\{i:03d}" for i in range(60)))
        preview, _ = _blocked(selected)
        block = preview["lines_breaking_a_rule"]
        # 150 lines break two rules each, 60 one: 210 lines, 360 rules
        assert block["count"] == 210
        assert len(block["lines"]) == 200


# ---------------------------------------------------------------------------
# The warnings, which never block
# ---------------------------------------------------------------------------

class TestTheWarnings:

    def test_a_pseudonym_putting_a_name_back(self, selected):
        _write_names(selected, "Ashdale = Participant A1",
                     "Quorvin Ashdale = Participant Ashdale",
                     "Brisemar Tull = Participant B")
        answer = _preview(selected)
        assert answer["preview"]["pseudonyms_putting_a_name_back"] == {
            "count": 1, "lines": [7]}
        assert server.SAVE_NAMES_LIST_PUT_BACK in answer["warnings"]
        # fix round 1: what Exegete's imports do, and what an import
        # applying the list entry by entry does
        assert ("so where Exegete applies the list it puts that name back; "
                "an import that applies the list one entry at a time, as "
                "QualCoder's does, can replace it again, so the two store "
                "different text.") in server.SAVE_NAMES_LIST_PUT_BACK

    def test_its_own_name_put_back(self, selected):
        _write_names(selected, "Quorvin = Quorvin Junior")
        answer = _preview(selected)
        assert answer["preview"]["pseudonyms_putting_a_name_back"][
            "lines"] == [6]

    def test_checked_beside_lines_to_correct(self, selected):
        """Where the design was silent: with lines to correct, the
        warning is checked on the lines that need none, so the researcher
        hears of it in the same round."""
        _write_names(selected, "Ashdale = Participant A1",
                     "Quorvin Ashdale = Participant Ashdale", "Quorvin",
                     "Q = Participant Q")
        preview, answer = _blocked(selected)
        assert preview["lines_breaking_a_rule"]["count"] == 1
        assert preview["pseudonyms_putting_a_name_back"]["lines"] == [7]
        assert server.SAVE_NAMES_LIST_PUT_BACK in answer["warnings"]

    def test_a_kept_entry_putting_a_name_back_is_counted(self, selected):
        _write_names(selected, "Ashdale = Participant A1")
        _write_list(selected, [("Brisemar = Tull", "Mr Ashdale")])
        answer = _preview(selected)
        block = answer["preview"]["pseudonyms_putting_a_name_back"]
        assert block == {"count": 0, "lines": [], "kept_entries": 1}
        # fix round 1: where such an entry can be changed, since it is on
        # no line
        assert answer["warnings"] == [
            server.SAVE_NAMES_LIST_PUT_BACK + " "
            + server.SAVE_NAMES_LIST_PUT_BACK_KEPT]
        assert ("on no line of the names file: the researcher can change "
                "them in pseudonyms.json") in \
            server.SAVE_NAMES_LIST_PUT_BACK_KEPT

    def test_one_pseudonym_on_more_than_one_line(self, selected):
        _write_names(selected, "Quorvin Ashdale = Participant Q",
                     "Quorvin = Participant Q", "Brisemar = Participant B",
                     "Ashdale = Participant Q")
        answer = _preview(selected)
        assert answer["preview"]["pseudonyms_on_more_than_one_line"] == {
            "count": 3, "lines": [6, 7, 9]}
        assert SHARED in answer["warnings"]
        assert server.SAVE_NAMES_LIST_SHARED == SHARED

    def test_no_warning_on_a_clean_list(self, selected):
        _write_names(selected, GOOD, "Brisemar Tull = Participant B")
        answer = _preview(selected)
        assert "warnings" not in answer
        assert answer["preview"]["pseudonyms_putting_a_name_back"] == {
            "count": 0, "lines": []}

    def test_a_names_file_older_than_the_list(self, selected):
        """The lead's answer: entries of the list on no line make the
        preview warn, and the researcher decides."""
        _write_list(selected, [("Quorvin Ashdale", "Participant Q"),
                               ("Brisemar Tull", "Participant B")])
        _write_names(selected, GOOD)
        answer = _preview(selected)
        assert answer["preview"]["effect"]["removed"] == 1
        assert server.SAVE_NAMES_LIST_REMOVES in answer["warnings"]
        assert "ask the researcher which" in server.SAVE_NAMES_LIST_REMOVES
        # fix round 1: how to find those entries, and the way back
        for words in (
                "To find them, they can compare the file with "
                "pseudonyms.json, in the project folder, in a text editor",
                "or they can rename the names file, leaving it in the "
                "project's Exegete folder, and you call prepare_names_list "
                "for a new one made from the list",
                "The backup made before the save keeps the list as it "
                "was."):
            assert words in server.SAVE_NAMES_LIST_REMOVES, words

    def test_a_pseudonym_the_save_would_change(self, selected):
        """Fix round 1: an older names file can change a pseudonym back,
        so a change warns as a removal does, and the researcher decides."""
        _write_list(selected, [("Quorvin Ashdale", "Participant Z")])
        _write_names(selected, GOOD)
        answer = _preview(selected)
        assert answer["preview"]["effect"]["changed"] == 1
        assert answer["warnings"] == [server.SAVE_NAMES_LIST_CHANGES]
        for words in ("(effect.changed counts them)",
                      "That is right if the researcher changed those "
                      "pseudonyms in the names file.",
                      "the older pseudonyms would come back: ask the "
                      "researcher which.",
                      "documents imported later would give those people "
                      "other pseudonyms than earlier ones."):
            assert words in server.SAVE_NAMES_LIST_CHANGES, words

    @pytest.mark.parametrize("real_name", [
        "Ann Lee Jr.", "Smith (Jr)", "Ann [Lee", "C:\\Users", "(Jo) Ann",
        "Ann|Bob", "Jo Ann?", "Ann+", "Ann*", "^Ann", "Ann$", "Ann{2}",
        "Ann-", "'Ann", "Jose\u0301"])
    def test_a_real_name_some_imports_read_as_a_pattern(self, selected,
                                                        real_name):
        """Fix round 1: a warning by line number, never blocking, for a
        real name QualCoder 3.8.2's text import (and 4.0's survey import)
        cannot find as written."""
        _write_names(selected, GOOD, f"{real_name} = Participant P")
        answer = _preview(selected)
        assert answer["preview"]["real_names_read_as_patterns"] == {
            "count": 1, "lines": [7]}
        assert server.SAVE_NAMES_LIST_PATTERN in answer["warnings"]

    def test_the_pattern_warning_says_what_and_for_whom(self):
        text = server.SAVE_NAMES_LIST_PATTERN
        for words in ("(one of \\ [ ] ( ) { } ^ $ | ? * +)",
                      "Exegete's imports replace them as written.",
                      "QualCoder 3.8.2's text and survey imports, and "
                      "QualCoder 4.0's survey import and its replacement of "
                      "a document with a newer file",
                      "for those who use them, such a name may be left in "
                      "the text, stop the import with an error, or replace "
                      "other words."):
            assert words in text, words

    @pytest.mark.parametrize("value", [
        "Ann Lee Jr.", "Smith (Jr)", "Ann [Lee", "C:\\Users", "(Jo) Ann",
        "Ann|Bob", "Jo Ann?", "Ann+", "Ann*", "^Ann", "Ann$", "Ann{2}",
        "Ann-", "'Ann", "Jose\u0301"])
    def test_flagged_names_are_not_found_by_3_8_2s_replacement(self, value):
        """QualCoder 3.8.2's replacement, mirrored (`manage_files.py`
        line 2039 at 3.8.2): each name the warning flags is left, stops
        the import, or replaces something else."""
        assert server._read_as_a_pattern(value)
        try:
            out = re.sub(rf"\b{value}\b", "P", f"said {value} today")
        except re.error:
            out = None
        assert out != "said P today", value

    @pytest.mark.parametrize("value", [
        "Ann", "Mary Ann", "J. Smith", "Smith, Jane", "O'Brien",
        "Jean-Paul", "Élodie Marchbank", "张伟", "Ann_", "Room 4"])
    def test_names_3_8_2s_replacement_finds_are_not_flagged(self, value):
        assert not server._read_as_a_pattern(value)
        assert re.sub(rf"\b{value}\b", "P", f"said {value} today") == \
            "said P today"

    def test_no_warning_on_a_clean_list_of_ordinary_names(self, selected):
        _write_names(selected, GOOD, "Jean-Paul O'Brien = Participant J",
                     "Smith, Jane = Participant S")
        answer = _preview(selected)
        assert answer["preview"]["real_names_read_as_patterns"] == {
            "count": 0, "lines": []}
        assert answer["preview"]["kept_entries_with_a_backslash"] == 0
        assert "warnings" not in answer


# ---------------------------------------------------------------------------
# The effect against the list now
# ---------------------------------------------------------------------------

class TestTheEffect:

    def test_against_a_list_in_a_dialogs_order(self, selected):
        """A list as QualCoder's Pseudonyms dialog leaves it, in the order
        the names were entered (the shorter first here)."""
        _write_list(selected, [("Tull", "Participant T"),
                               ("Brisemar Tull", "Participant B"),
                               ("Ottoline", "Participant O"),
                               ("Zeno Vask", "Participant Z")])
        _write_names(selected, "Tull = Participant T",
                     "Brisemar Tull = Participant C",
                     "Quorvin Ashdale = Participant Q",
                     "Zeno Vask = Participant Z")
        effect = _preview(selected)["preview"]["effect"]
        assert effect == {"entries_after": 4, "added": 1, "changed": 1,
                          "removed": 1, "unchanged": 2,
                          "kept_entries_the_file_cannot_hold": 0,
                          "order_changed": True}

    def test_no_list_yet(self, selected):
        _write_names(selected, GOOD, "Brisemar Tull = Participant B")
        effect = _preview(selected)["preview"]["effect"]
        assert effect == {"entries_after": 2, "added": 2, "changed": 0,
                          "removed": 0, "unchanged": 0,
                          "kept_entries_the_file_cannot_hold": 0,
                          "order_changed": False}

    def test_the_same_order_already(self, selected):
        _write_list(selected, [("Brisemar Tull", "Participant B"),
                               ("Ottoline", "Participant O")])
        _write_names(selected, "Ottoline = Participant O",
                     "Brisemar Tull = Participant B")
        effect = _preview(selected)["preview"]["effect"]
        assert effect["order_changed"] is False
        assert effect["unchanged"] == 2

    def test_kept_entries_counted_and_kept(self, selected):
        _write_list(selected, [("Brisemar = Tull", "Participant B"),
                               ("Ottoline", "Participant O")])
        _write_names(selected, GOOD)
        effect = _preview(selected)["preview"]["effect"]
        assert effect["kept_entries_the_file_cannot_hold"] == 1
        assert effect["removed"] == 1
        assert effect["entries_after"] == 2

    def test_a_list_with_one_name_twice(self, selected):
        """A list edited by hand may give a real name twice: the first
        entry is compared, and the other is counted as removed, since
        the saved list holds one entry per name."""
        _write_list(selected, [("Ottoline", "Participant O"),
                               ("Ottoline", "Participant P")])
        _write_names(selected, "Ottoline = Participant O")
        effect = _preview(selected)["preview"]["effect"]
        assert (effect["unchanged"], effect["removed"],
                effect["entries_after"]) == (1, 1, 1)


# ---------------------------------------------------------------------------
# The token
# ---------------------------------------------------------------------------

class TestTheToken:

    def test_only_with_nothing_to_correct(self, selected):
        _write_names(selected, GOOD, "Quorvin")
        answer = _save()
        assert "preview_token" not in answer
        _write_names(selected, GOOD)
        answer = _preview(selected)
        assert answer["requires_confirmation"] is True
        assert answer["hint"] == HINT
        assert answer["execute_with"] == {
            "tool": "save_names_list",
            "arguments": {"preview_token": answer["preview_token"]}}
        assert answer["token_valid_for_minutes"] == 60

    def test_it_binds_no_argument(self):
        assert preview_tokens.canonical_args("save_names_list") == {}
        assert "save_names_list" not in preview_tokens.KEYED_BIND

    def test_refused_after_the_names_file_changes(self, selected):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        # another pseudonym, the same counts
        _write_names(selected, "Quorvin Ashdale = Participant R")
        answer = _save(token)
        assert answer["reason"] == "project_changed"
        assert answer["nothing_changed"] is True
        assert not (selected / "pseudonyms.json").exists()
        # fix round 1: in the names file's words, not of rows
        assert answer["error"].startswith(TOKEN_CHANGED)
        assert answer["error"].endswith(
            "call save_names_list without preview_token for a fresh "
            "preview, show the researcher what it says, then save on their "
            "word. Nothing was changed.")
        assert "rows" not in answer["error"]

    def test_refused_after_the_list_changes(self, selected):
        _write_names(selected, GOOD)
        _write_list(selected, [("Brisemar = Tull", "Participant B")])
        token = _preview(selected)["preview_token"]
        _write_list(selected, [("Brisemar = Tull", "Participant C")])
        before = _list_bytes(selected)
        assert _save(token)["reason"] == "project_changed"
        assert _list_bytes(selected) == before

    def test_refused_once_expired(self, selected, monkeypatch):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        later = int(time.time()) + preview_tokens.TOKEN_MAX_AGE_SECONDS + 5
        monkeypatch.setattr(preview_tokens, "_now", lambda: later)
        answer = _save(token)
        assert answer["reason"] == "token_expired"
        assert not (selected / "pseudonyms.json").exists()

    def test_refused_when_not_one_exegete_issued(self, selected):
        _write_names(selected, GOOD)
        assert _save("qcp1.1.deadbeef.0")["reason"] == "token_malformed"

    def test_refused_when_issued_for_another_tool(self, selected):
        _write_names(selected, GOOD)
        _preview(selected)
        other = preview_tokens.issue("prune_backups", {
            "keep_last": 1, "older_than_days": None},
            server._token_project(), "x")
        assert _save(other)["reason"] in ("token_other_operation",
                                          "project_changed")

    def test_with_lines_to_correct_now_the_token_is_refused(self, selected):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        _write_names(selected, GOOD, "Quorvin")
        assert _save(token)["reason"] == "project_changed"

    def test_a_refusal_before_the_token_is_read(self, selected):
        """A names file gone since the preview: its own refusal, before
        the token is checked (as restore_backup checks its backup)."""
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        _names(selected).unlink()
        _refused(_save(token), "no_names_file", NO_NAMES_FILE)


# ---------------------------------------------------------------------------
# The save
# ---------------------------------------------------------------------------

def _backups(folder):
    return sorted(p.name for p in folder.parent.iterdir()
                  if "_backup_" in p.name)


class TestTheSave:

    def test_a_backup_first_then_the_list(self, selected, caplog):
        _write_list(selected, [("Ottoline", "Participant O")])
        before = _list_bytes(selected)
        _write_names(selected, GOOD, "Ottoline = Participant O")
        token = _preview(selected)["preview_token"]
        caplog.set_level(logging.INFO)
        answer = _save(token)
        assert answer["success"] is True
        assert answer["entries"] == 2
        assert answer["note"] == NOTE
        assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d",
                            answer["saved_at"])
        assert list(answer) == ["success", "entries", "backup", "saved_at",
                                "note"]
        assert _backups(selected) == [answer["backup"]]
        # the backup holds the list as it was
        assert (selected.parent / answer["backup"] / "pseudonyms.json"
                ).read_bytes() == before
        # and the list is the names file's now, renamed into place
        assert _saved(selected) == [
            {"original": "Quorvin Ashdale", "pseudonym": "Participant Q"},
            {"original": "Ottoline", "pseudonym": "Participant O"}]
        assert _no_temporary_file(selected)
        assert LOG_LINE % 2 in [r.getMessage() for r in caplog.records]

    def test_the_bytes_in_qualcoders_format(self, selected, tmp_path):
        """ASCII as json.dump's defaults write it, indent 2, the longest
        real name first, a stable sort (equal lengths in the names file's
        order, then the kept entries in the list's), extra keys kept on
        unchanged entries and on kept ones."""
        _write_list(selected, [("Ann", "Participant A2"),
                               ("Brisemar = Tull", "Participant K",),
                               ("Bea", "Participant B2"),
                               ("Zoë", "Participant Z")],
                    e0={"note": 1}, e1={"colour": "red"}, e3={"x": [1]})
        _write_names(selected, "Bea = Participant B3", "Ann = Participant A2",
                     "Mary Ann = Participant M", "Élodie = Participant É",
                     "Smith, Jane = Participant S", "Zoë = Participant Z",
                     "Kit = Participant C")
        token = _preview(selected)["preview_token"]
        assert _save(token)["entries"] == 8
        raw = _list_bytes(selected)
        raw.decode("ascii")
        expected = [
            {"original": "Brisemar = Tull", "pseudonym": "Participant K",
             "colour": "red"},
            {"original": "Smith, Jane", "pseudonym": "Participant S"},
            {"original": "Mary Ann", "pseudonym": "Participant M"},
            {"original": "Élodie", "pseudonym": "Participant É"},
            {"original": "Bea", "pseudonym": "Participant B3"},
            {"original": "Ann", "pseudonym": "Participant A2", "note": 1},
            {"original": "Zoë", "pseudonym": "Participant Z", "x": [1]},
            {"original": "Kit", "pseudonym": "Participant C"},
        ]
        # QualCoder's own statement (pseudonyms.py:92-93), no encoding
        # argument, on the same list: the same bytes, line endings
        # included, on every system
        reference = tmp_path / "reference.json"
        with open(reference, "w") as output_file:
            json.dump(expected, output_file, indent=2)
        assert raw == reference.read_bytes()
        assert json.loads(raw.decode("ascii")) == expected

    def test_the_names_file_is_never_changed(self, selected):
        raw = _write_names(selected, GOOD, "# a note of the researcher's",
                           "", ending="\r\n", mark=True)
        before = _names(selected).stat()
        token = _preview(selected)["preview_token"]
        _save(token)
        assert _names(selected).read_bytes() == BOM + raw
        after = _names(selected).stat()
        assert after.st_mtime_ns == before.st_mtime_ns

    @pytest.mark.skipif(not POSIX, reason="POSIX modes")
    def test_a_new_list_is_the_owners_alone(self, selected):
        _write_names(selected, GOOD)
        _save(_preview(selected)["preview_token"])
        mode = stat.S_IMODE((selected / "pseudonyms.json").stat().st_mode)
        assert mode == 0o600

    @pytest.mark.skipif(not POSIX, reason="POSIX modes")
    def test_an_existing_lists_mode_is_kept(self, selected):
        _write_list(selected, [("Ottoline", "Participant O")])
        os.chmod(selected / "pseudonyms.json", 0o640)
        _write_names(selected, GOOD)
        _save(_preview(selected)["preview_token"])
        mode = stat.S_IMODE((selected / "pseudonyms.json").stat().st_mode)
        assert mode == 0o640

    def test_a_link_made_since_the_preview_is_refused(self, selected,
                                                      tmp_path):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        target = tmp_path / "kept.json"
        target.write_text("[]", encoding="utf-8")
        if not _symlink(selected / "pseudonyms.json", target):
            pytest.skip("links cannot be made here")
        _refused(_save(token), "pseudonyms_json_is_a_link")
        assert target.read_text(encoding="utf-8") == "[]"
        assert _backups(selected) == []

    @pytest.mark.skipif(not POSIX or os.geteuid() == 0,
                        reason="a mode the system enforces")
    def test_a_list_made_read_only_since_the_preview_is_refused(
            self, selected):
        _write_list(selected, [("Ottoline", "Participant O")])
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        os.chmod(selected / "pseudonyms.json", 0o444)
        before = _list_bytes(selected)
        _refused(_save(token), "pseudonyms_json_read_only")
        assert _list_bytes(selected) == before
        assert _backups(selected) == []

    def test_the_lock_file_refuses(self, selected):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        (selected / "project_in_use.lock").write_text(
            f"someone\n{time.time()}\n", encoding="utf-8")
        answer = _save(token)
        assert "QualCoder" in answer["error"] and "open" in answer["error"]
        assert not (selected / "pseudonyms.json").exists()
        assert _backups(selected) == []
        # fix round 1: a reason, as every other refusal of the tool has
        assert answer["reason"] == "project_locked"
        assert answer["nothing_changed"] is True

    def test_no_backup_no_save(self, selected, monkeypatch):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]

        def fails(folder, report=None):
            raise OSError(28, "No space left on device")
        monkeypatch.setattr(server, "backup_project", fails)
        assert _save(token) == {"error": NO_BACKUP, "reason": "no_backup",
                                "nothing_changed": True}
        assert not (selected / "pseudonyms.json").exists()


def _after_the_backup(monkeypatch, then):
    """backup_project as it is, then `then(folder)`: what happens between
    the token's check and the lock."""
    real = server.backup_project

    def backup(folder, report=None):
        made = real(folder, report=report)
        then(Path(folder))
        return made
    monkeypatch.setattr(server, "backup_project", backup)


def _no_temporary_file(folder):
    return [p.name for p in folder.iterdir()
            if p.name.startswith("pseudonyms.json.")] == []


class TestBetweenTheTokenAndTheWrite:

    def test_a_change_is_refused_with_nothing_written(self, selected,
                                                      monkeypatch):
        _write_list(selected, [("Ottoline", "Participant O")])
        before = _list_bytes(selected)
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        _after_the_backup(monkeypatch, lambda folder: _write_names(
            folder, "Quorvin Ashdale = Participant R"))
        answer = _save(token)
        assert answer["reason"] == "project_changed"
        assert answer["nothing_changed"] is True
        assert answer["error"].endswith(
            " A backup had already been taken before the change was "
            "detected; it is unchanged and can be pruned.")
        # fix round 1: in the names file's words, not of rows
        assert answer["error"].startswith(TOKEN_CHANGED_UNDER_THE_LOCK)
        assert _backups(selected) == [answer["backup"]]
        assert _list_bytes(selected) == before
        assert _no_temporary_file(selected)

    def test_a_refusal_found_under_the_lock_names_the_backup(
            self, selected, monkeypatch, tmp_path):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        target = tmp_path / "kept.json"
        target.write_text("[]", encoding="utf-8")
        if not _symlink(tmp_path / "probe", target):
            pytest.skip("links cannot be made here")
        _after_the_backup(monkeypatch, lambda folder: _symlink(
            folder / "pseudonyms.json", target))
        answer = _save(token)
        assert answer["reason"] == "pseudonyms_json_is_a_link"
        assert answer["nothing_changed"] is True
        assert _backups(selected) == [answer["backup"]]
        assert answer["error"].endswith("it is unchanged and can be "
                                        "pruned.")
        assert target.read_text(encoding="utf-8") == "[]"

    def test_a_failed_write_leaves_no_temporary_file(self, selected,
                                                     monkeypatch):
        _write_list(selected, [("Ottoline", "Participant O")])
        before = _list_bytes(selected)
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]

        class Failing:
            dumps = staticmethod(json.dumps)
            loads = staticmethod(json.loads)
            JSONDecodeError = json.JSONDecodeError

            @staticmethod
            def dump(data, handle, **kwargs):
                handle.write("[\n  {")
                raise OSError(28, "No space left on device")
        _after_the_backup(monkeypatch, lambda folder: monkeypatch.setattr(
            server, "json", Failing))
        answer = _save(token)
        assert answer["reason"] == "not_saved"
        assert answer["error"] == (
            f"pseudonyms.json could not be written (OSError), so the names "
            f"list was not saved and is as it was. The backup made first is "
            f"kept: {answer['backup']}.")
        assert _list_bytes(selected) == before
        assert _no_temporary_file(selected)

    def test_a_failed_rename_leaves_no_temporary_file(self, selected,
                                                      monkeypatch):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]

        def refuses(source, target):
            raise PermissionError(13, "Permission denied")
        _after_the_backup(monkeypatch, lambda folder: monkeypatch.setattr(
            server.os, "replace", refuses))
        answer = _save(token)
        monkeypatch.undo()
        assert answer["reason"] == "not_saved"
        assert "(PermissionError)" in answer["error"]
        assert not (selected / "pseudonyms.json").exists()
        assert _no_temporary_file(selected)

    def test_the_lock_file_appearing_after_the_check(self, selected,
                                                     monkeypatch):
        _write_names(selected, GOOD)
        token = _preview(selected)["preview_token"]
        _after_the_backup(monkeypatch, lambda folder: (
            folder / "project_in_use.lock").write_text(
                f"someone\n{time.time()}\n", encoding="utf-8"))
        answer = _save(token)
        assert "QualCoder" in answer["error"]
        assert answer["error"].endswith(
            f"The names list was not saved; the backup made first is kept: "
            f"{answer['backup']}.")
        assert answer["nothing_changed"] is True
        # fix round 1: a reason, as every other refusal of the tool has
        assert answer["reason"] == "project_locked"
        assert not (selected / "pseudonyms.json").exists()


# ---------------------------------------------------------------------------
# No name anywhere: the whole loop, every answer and every log line
# ---------------------------------------------------------------------------

REAL = ("Quillon Vantreese", "Élodie Marchbank", "Brisemar Tullaway",
        "Ottoline Faverdy")
PSEUDONYMS = ("Participant Kestrel", "Participant Héron",
              "Participant Wrenlow", "Participant Larkspur")
# Fix round 1: an entry of the list the names file cannot hold (its real
# name holds =), kept through the loop
KEPT = ("Wendeline = Corrabay", "Participant Sorrelby")


class TestNoNameAnywhere:

    def _loop(self, selected, tmp_path):
        """prepare_names_list, a preview with every problem, a clean
        preview, the save, get_current_project in both sets, list_backups,
        restore_backup's preview and import_documents' preview of a
        document that holds the names; every answer."""
        from exegete import import_paths
        answers = {"prepare": [], "save": [], "other": []}
        _write_list(selected, [(REAL[3], PSEUDONYMS[3]), KEPT])
        answers["prepare"].append(server.prepare_names_list())
        made = _names(selected).read_text(encoding="utf-8-sig")
        assert REAL[3] in made
        _write_names(selected, f"{REAL[0]} = {PSEUDONYMS[0]}", REAL[1],
                     f"= {PSEUDONYMS[1]}", f"{REAL[2]} = {REAL[0]}",
                     f"{REAL[0]} = {PSEUDONYMS[2]}",
                     f"{REAL[1]} = P\\{PSEUDONYMS[1]}",
                     f"{REAL[2]} = Q")
        answers["save"].append(server.save_names_list())
        _write_names(selected, *(f"{r} = {p}" for r, p in
                                 zip(REAL, PSEUDONYMS)))
        preview = server.save_names_list()
        answers["save"].append(preview)
        saved = server.save_names_list(
            preview_token=json.loads(preview)["preview_token"])
        answers["save"].append(saved)
        assert json.loads(saved)["success"] is True
        for mode in ("full", "core"):
            server._apply_toolset(mode)
            answers["other"].append(server.get_current_project())
        server._apply_toolset("full")
        backups = server.list_backups()
        answers["other"].append(backups)
        backup = selected.parent / json.loads(saved)["backup"]
        answers["other"].append(server.restore_backup(str(backup)))
        interviews = tmp_path / "interviews"
        interviews.mkdir()
        (interviews / "visit.txt").write_text(
            "A visit. " + " and ".join(REAL) + " spoke.\n", encoding="utf-8")
        excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
        real_hidden = import_paths.hidden_step
        import_paths.hidden_step = lambda step, info: (
            os.path.normcase(str(step)) not in excused
            and real_hidden(step, info))
        try:
            answers["other"].append(server.import_documents(
                [str(interviews / "visit.txt")]))
        finally:
            import_paths.hidden_step = real_hidden
        return answers

    def test_no_real_name_in_any_answer_log_line_or_token(
            self, selected, asked, tmp_path, caplog, capsys):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        caplog.set_level(logging.DEBUG)
        try:
            answers = self._loop(selected, tmp_path)
        finally:
            logging.getLogger().removeHandler(handler)
        printed = capsys.readouterr()
        logs = "\n".join([caplog.text, printed.err, printed.out,
                          stream.getvalue()]
                         + [r.getMessage() for r in caplog.records])
        assert "save_names_list saved the project's names list (5 " \
               "entries)." in stream.getvalue()
        everything = "\n".join(sum(answers.values(), [])) + "\n" + logs
        for name in REAL + KEPT[:1]:
            assert name not in everything, name
            assert json.dumps(name)[1:-1] not in everything, name
            for part in name.split():
                if len(part) >= 3:
                    assert part not in everything, part
        own = "\n".join(answers["prepare"] + answers["save"])
        for pseudonym in PSEUDONYMS + KEPT[1:]:
            assert pseudonym not in own, pseudonym
            assert json.dumps(pseudonym)[1:-1] not in own, pseudonym
        # the import's preview did see the names, by count
        assert json.loads(answers["other"][-1]).get("preview_token")
        # and the preview with every problem had every kind of problem
        blocked = json.loads(answers["save"][0])["preview"]
        for key in BLOCKING:
            assert blocked[key]["count"] >= 1, key

    def test_the_tokens_hold_no_name(self, selected):
        _write_names(selected, *(f"{r} = {p}" for r, p in
                                 zip(REAL, PSEUDONYMS)))
        token = _preview(selected)["preview_token"]
        assert re.fullmatch(r"qcp1\.\d+\.[0-9a-f]{8}\.[0-9a-f]{32}", token)


# ---------------------------------------------------------------------------
# As Windows' Notepad saves the file, and in a synced folder
# ---------------------------------------------------------------------------

class TestWhereTheFileComesFrom:

    def test_a_file_as_notepad_saves_it_through_to_the_save(self, selected):
        """UTF-8 with a mark, lines ending in CR LF."""
        _write_names(selected, "Renée Okonkwo = Participant R",
                     "O'Brien -> Participant O", ending="\r\n", mark=True)
        answer = _preview(selected)
        assert answer["preview"]["lines_read"] == 2
        _save(answer["preview_token"])
        assert _saved(selected) == [
            {"original": "Renée Okonkwo", "pseudonym": "Participant R"},
            {"original": "O'Brien", "pseudonym": "Participant O"}]

    def test_a_file_in_windows_default_encoding_is_refused(self, selected):
        raw = (HEADER + "Renée Okonkwo = Participant R\n").replace(
            "\n", "\r\n").encode("cp1252")
        _names(selected).write_bytes(raw)
        _refused(_save(), "names_file_not_utf8", NOT_UTF8)

    def test_the_whole_loop_in_a_synced_folder(self, tmp_path, monkeypatch,
                                               asked):
        """A project in a cloud drive's folder on a Mac
        (~/Library/CloudStorage), under a scratch home of its own."""
        from test_v012_pseudonymise_tool import build_project
        from track5_helpers import write_fixture_sidecar
        home = tmp_path / "home"
        cloud = home / "Library" / "CloudStorage" / "OneDrive-Test"
        folder = build_project(cloud / "Study three.qda")
        write_fixture_sidecar(str(folder))
        if hasattr(os, "chflags") and sys.platform == "darwin":
            os.chflags(home / "Library", stat.UF_HIDDEN)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        original = (server.db, server.current_project_path)
        try:
            assert json.loads(server.select_project(str(folder))).get(
                "success") is not False
            assert json.loads(server.prepare_names_list())["created"]
            _write_names(folder, "Quillon Vantreese = Participant K")
            answer = _preview(folder)
            assert _save(answer["preview_token"])["success"] is True
            assert _saved(folder) == [{"original": "Quillon Vantreese",
                                       "pseudonym": "Participant K"}]
        finally:
            if server.db is not None:
                server.db.close()
            server.db, server.current_project_path = original


# ---------------------------------------------------------------------------
# What it says, where it is served, how it is marked
# ---------------------------------------------------------------------------

class TestWhatItSays:

    def test_the_description_word_for_word(self):
        """The design's words, then the Args section every tool with an
        argument carries (tests/test_v014_server_wide.py requires it)."""
        server._apply_toolset("full")
        tool = server.mcp._tool_manager._tools["save_names_list"]
        assert _flat(tool.description) == DESCRIPTION + (
            " Args: preview_token: the token from this save's preview; "
            "omit it to get the preview")
        assert list(tool.parameters["properties"]) == ["preview_token"]
        assert "required" not in tool.parameters

    def test_the_texts_word_for_word(self):
        assert server.NO_NAMES_FILE == NO_NAMES_FILE
        assert server.NAMES_FILE_NOT_READABLE == NOT_READABLE
        assert server.NAMES_FILE_NOT_UTF8 == NOT_UTF8
        assert server.NAMES_FILE_EMPTY == EMPTY
        assert server.NAMES_LIST_UNREADABLE_ADVICE == UNREADABLE_ADVICE
        assert server.RULE_NOT_DESCRIBED == RULE_NOT_DESCRIBED
        assert server.SAVE_NAMES_LIST_HINT == HINT
        assert server.NO_BACKUP_NAMES_LIST == NO_BACKUP
        assert server.SAVE_NAMES_LIST_NOTE == NOTE

    def test_no_text_presumes_qualcoder_or_says_the_server(self):
        own = [value for key, value in vars(server).items()
               if isinstance(value, str) and key.startswith(
                   ("SAVE_NAMES_LIST", "NO_NAMES_FILE", "NAMES_FILE_",
                    "NAMES_LIST_", "RULE_NOT", "NO_BACKUP_NAMES",
                    "BACKUP_KEPT"))]
        own += list(server.NAMES_FILE_NOT_READABLE.values())
        assert len(own) >= 20
        for text in own + [DESCRIPTION]:
            assert "—" not in text
            assert "the server" not in text
            assert "better than" not in text
        # QualCoder named only for its format, in sentences about its
        # imports and dialog (fix round 1, beside pseudonymise_source's
        # words for the same list), and in the hint given on its window's
        # signs
        naming = sorted(key for key, value in vars(server).items()
                        if isinstance(value, str) and value in own
                        and "QualCoder" in value)
        assert naming == [
            "SAVE_NAMES_LIST_GUI_HINT", "SAVE_NAMES_LIST_KEPT_BACKSLASH",
            "SAVE_NAMES_LIST_NOTE", "SAVE_NAMES_LIST_PATTERN",
            "SAVE_NAMES_LIST_PUT_BACK"]
        assert "QualCoder's text and transcript imports, for those who use " \
            "them," in server.SAVE_NAMES_LIST_NOTE
        assert "for those who use them" in server.SAVE_NAMES_LIST_PATTERN
        assert server.SAVE_NAMES_LIST_GUI_HINT.startswith(
            "This project appears to be open in QualCoder ({signs}).")
        assert DESCRIPTION.count("QualCoder") == 1
        assert "in QualCoder's format" in DESCRIPTION

    def test_the_window_signs_are_passed_on_outside_the_token(
            self, selected, monkeypatch):
        """Fix round 1: QualCoder 4.0's window signs in the preview, with a
        hint naming its Pseudonyms dialog, never a refusal, and outside
        the state the token signs."""
        signs = ["a QualCoder 4.0 file beside the project changed recently"]
        monkeypatch.setattr(server, "qualcoder_gui_signals",
                            lambda folder, **kwargs: list(signs))
        _write_names(selected, GOOD, "Quorvin")
        blocked = _save()["preview"]
        assert blocked["qualcoder_gui_signals"] == signs
        _write_names(selected, GOOD)
        answer = _preview(selected)
        assert answer["preview"]["qualcoder_gui_signals"] == signs
        hint = answer["preview"]["qualcoder_gui_hint"]
        assert hint == server.SAVE_NAMES_LIST_GUI_HINT.format(
            signs=signs[0])
        assert "QualCoder's Pseudonyms dialog keeps the list it read" in hint
        signs.clear()
        assert _save(answer["preview_token"])["success"] is True

    def test_no_window_signs_no_hint(self, selected, monkeypatch):
        monkeypatch.setattr(server, "qualcoder_gui_signals",
                            lambda folder, **kwargs: [])
        _write_names(selected, GOOD)
        preview = _preview(selected)["preview"]
        assert preview["qualcoder_gui_signals"] == []
        assert "qualcoder_gui_hint" not in preview

    def test_in_full_not_in_core(self):
        server._apply_toolset("full")
        assert "save_names_list" in server.mcp._tool_manager._tools
        assert "save_names_list" not in server.CORE_TOOLSET
        server._apply_toolset("core")
        assert "save_names_list" not in server.mcp._tool_manager._tools
        server._apply_toolset("full")

    def test_marked_as_changing_and_asking_every_time(self):
        server._apply_toolset("full")
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        hints = tools["save_names_list"].annotations
        assert (hints.readOnlyHint, hints.destructiveHint,
                hints.idempotentHint, hints.openWorldHint) == (
                    False, True, False, False)
        assert server.TOOL_META["save_names_list"] == {
            "anthropic/requiresUserInteraction": True}

    def test_prepare_names_list_points_to_it(self):
        server._apply_toolset("full")
        tool = server.mcp._tool_manager._tools["prepare_names_list"]
        assert ("say when the list is ready; then call save_names_list. "
                "Never open or read the file yourself.") in _flat(
                    tool.description)
        assert server.PREPARE_NAMES_LIST_FILL_IN.endswith(
            "tell you when the list is ready; then call save_names_list.")
        assert server.PREPARE_NAMES_LIST_FILL_IN in \
            server.PREPARE_NAMES_LIST_NEXT_STEP

    def test_the_brief_names_it_among_the_two_step_changes(self):
        brief = _flat(server.read_brief())
        assert ("pseudonymising a file, importing documents, saving the "
                "names list and correcting the researcher's coder name take "
                "two steps") in brief


# ---------------------------------------------------------------------------
# The guard: each refusal the engine's check can give is met first by a
# check the preview names
# ---------------------------------------------------------------------------

K1 = ("Brisemar = Tull", "Participant B")          # a kept entry
MANY = tuple(f"Name{i:04d} = Participant {i:04d}"
             for i in range(pseudo.MAX_ENTRIES + 1))
# (what the list breaks, the names file's lines, the list's entries)
GUARDED = [
    ("an empty list", ("# only a note",), []),
    ("more than 500 entries", MANY, []),
    ("white space at an end", (GOOD,), [(" Brisemar Tull", "Participant B")]),
    ("a control character", ("Quorvin\u0085Ashdale = Participant Q",), []),
    ("a line separator", ("Quorvin Ashdale = Participant Q",), []),
    ("a direction character", ("Quorvin Ashdale = Partic‮ipant Q",),
     []),
    ("five #", ("Quorvin Ashdale = Participant #####",), []),
    ("a real name too short", ("Q = Participant Q",), []),
    ("a real name too long", ("x" * 201 + " = Participant Q",), []),
    ("a pseudonym too short", ("Quorvin Ashdale = Q1",), []),
    ("a pseudonym too long", ("Quorvin Ashdale = " + "y" * 201,), []),
    ("an emoji", ("Quorvin Ashdale = Participant \U0001f600",), []),
    ("a real name twice", (GOOD, "Quorvin Ashdale = Participant R"), []),
    ("kept entries with one real name", (GOOD,),
     [K1, ("Brisemar = Tull", "Participant C")]),
    ("a line's pseudonym a line's real name",
     (GOOD, "Brisemar Tull = Quorvin Ashdale"), []),
    ("a kept pseudonym a line's real name", (GOOD,),
     [("Brisemar = Tull", "Quorvin Ashdale")]),
    ("a line's pseudonym a kept real name",
     ("Quorvin Ashdale = #Brisemar Tull",),
     [("#Brisemar Tull", "Participant B")]),
    ("a kept pseudonym another kept real name", (GOOD,),
     [K1, ("Ottoline -> Faverdy", "Brisemar = Tull")]),
    ("a kept entry its own pseudonym", (GOOD,),
     [("Brisemar = Tull", "Brisemar = Tull")]),
    # fix round 1: the emoji's rule before the backslash's, which a kept
    # entry may break
    ("a kept entry holding an emoji and a backslash", (GOOD,),
     [("Brisemar = Tull", "P\U0001f600\\B")]),
]


class TestTheGuard:

    @pytest.mark.parametrize("what, lines, entries", GUARDED,
                             ids=[case[0] for case in GUARDED])
    def test_a_check_meets_each_refusal_first(self, selected, what, lines,
                                              entries):
        _write_names(selected, *lines)
        if entries:
            _write_list(selected, entries)
        parsed = names_file.parse(names_file.decode(
            _names(selected).read_bytes()))
        to_save = ([{"original": r, "pseudonym": p}
                    for _, r, p in parsed.pairs]
                   + [{"original": r, "pseudonym": p} for r, p in entries])
        # the engine refuses the list a save would write ...
        with pytest.raises(pseudo.MappingError):
            pseudo.validate_mapping(to_save, case_mode="exact",
                                    may_echo_names=False)
        # ... and the preview has already said why, by a check it names
        answer = _save()
        assert answer["reason"] in ("corrections_needed",
                                    "names_file_empty"), answer
        assert answer["reason"] != "rule_not_described"
        if answer["reason"] == "corrections_needed":
            preview = answer["preview"]
            assert any(preview[key]["count"] for key in BLOCKING) or \
                preview["too_many_names"] or \
                preview["kept_entries_in_conflict"]


# ---------------------------------------------------------------------------
# What was factored out of pseudonymise_source's save, and the order of
# equal lengths
# ---------------------------------------------------------------------------

class TestTheSharedParts:

    def test_the_merge_checks_through_the_shared_helper_first(
            self, selected, monkeypatch):
        """pseudonymise_source's save refuses a link and a read-only list
        through `_pseudonyms_json_check_writable`, before reading."""
        seen = []

        def check(path):
            seen.append(path)
            raise server._SaveRefused("pseudonyms_json_is_a_link", "probe")
        monkeypatch.setattr(server, "_pseudonyms_json_check_writable", check)
        monkeypatch.setattr(server, "read_project_pseudonyms_with_raw",
                            lambda folder: pytest.fail("read first"))
        _write_list(selected, [("Ottoline", "Participant O")])
        with pytest.raises(server._SaveRefused):
            server._pseudonyms_json_merge(selected, None)
        assert seen == [selected / "pseudonyms.json"]

    def test_the_writers_refusal_keeps_its_words(self, selected,
                                                 monkeypatch):
        def fails(folder, data, existing_mode=None):
            raise OSError(28, "No space left on device")
        monkeypatch.setattr(server, "_write_pseudonyms_json_data_tmp", fails)
        with pytest.raises(RuntimeError) as caught:
            server._write_pseudonyms_json_tmp(selected, [])
        assert str(caught.value).startswith(
            "The mapping could not be written into this project's folder "
            "for saving (OSError); the rewrite was rolled back with it, "
            "nothing was changed and no file was left behind.")

    def test_equal_lengths_the_names_file_then_the_kept_entries(
            self, selected):
        _write_list(selected, [("Ab = Cd", "Participant K"),
                               ("Ef -> G", "Participant L")])
        _write_names(selected, "Tullbro = Participant T",
                     "Ashdale = Participant A")
        _save(_preview(selected)["preview_token"])
        assert [e["original"] for e in _saved(selected)] == [
            "Tullbro", "Ashdale", "Ab = Cd", "Ef -> G"]


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

TOOLS_ENTRY = (
    "- `save_names_list(preview_token)` - **WRITES TO THE PROJECT** - Checks "
    "the names file and saves it as `pseudonyms.json`: a preview of counts "
    "and line numbers, never a name, then the save, after a backup. In the "
    "full tool set, not in core")


class TestTheDocuments:

    def test_tools_lists_it_after_prepare_names_list(self):
        tools = _read("TOOLS.md")
        lines = tools.splitlines()
        at = lines.index(TOOLS_ENTRY)
        assert lines[at - 1].startswith("- `prepare_names_list()` - ")
        assert lines[at + 1].startswith("- `create_project(")
        assert "registers 83 tools, two of them the earlier names" in \
            _flat(tools)

    def test_the_changelog_says_what_was_added(self):
        log = _read("CHANGELOG.md")
        unreleased = log[log.index("## [Unreleased]"):
                         log.index("## [0.14.3-alpha]")]
        heading = "### Added: the names list, filled in on your computer"
        part = unreleased[unreleased.index(heading):]
        part = _flat(part[:part.index("\n### ", 5)]).replace("**", "")
        for words in (
                # fix round 1: what the list is for, the two counted
                # blocks, the warnings added, the departures named
                "`save_names_list` saves the names file as the project's "
                "names list (in `full`, not in `core`): the list "
                "`import_documents` applies as documents come in. It takes "
                "two calls; Claude Code asks before both "
                "(`anthropic/requiresUserInteraction`).",
                "a preview of counts and line numbers, never a name",
                "and, as counts, more than 500 entries, or entries kept "
                "from the list that clash with the lines.",
                "While any of these needs correcting, nothing can be saved",
                "entries the save would remove from the list or give "
                "another pseudonym (the file may be older than the list), "
                "entries kept from the list whose pseudonym holds a "
                "backslash, and real names that some of QualCoder's imports "
                "read as a pattern",
                "it passes on the signs that QualCoder 4.0 may have the "
                "project open.",
                "A pseudonym on a line holding a backslash is refused, "
                "which QualCoder's Pseudonyms dialog accepts",
                "One pseudonym on several lines is written, with its "
                "warning, where the dialog refuses a second entry with a "
                "pseudonym already in use: forms of one person's name share "
                "one, and QualCoder reads such a list as it reads its own.",
                "there two names that overlap without either containing the "
                "other (Mary Ann and Ann Lee, in Mary Ann Lee) can still "
                "come out differently from Exegete's import",
                "QualCoder 3.8.2's text and survey imports, and QualCoder "
                "4.0's survey import and its replacement of a document with "
                "a newer file, put each real name into a pattern as it is "
                "written",
                "Documents already in the project keep their text: "
                "`pseudonymise_source` with `use_project_pseudonyms` "
                "replaces the names in them, a file at a time.",
                "the second call makes a backup of the project, then writes "
                "`pseudonyms.json` in QualCoder's format, the longest real "
                "name first,",
                "The names file itself is never changed, and stays the "
                "place to change the list."):
            assert words in part, words
        assert part.index("Then Exegete shows the file") < part.index(
            "`save_names_list` saves") < part.index(
            "What the save writes.") < part.index("Exports are not")
        # fix round 1: what upgrading means for a list already there
        upgrading = _flat(log[log.index("### Upgrading from 0.14.3"):
                              log.index("### Changed: one tool set")])
        assert ("- **Saving the names list replaces `pseudonyms.json`.** "
                "When you save the names file as the list "
                "(`save_names_list`), a backup of the project is made "
                "first; then the list holds what the file holds: entries on "
                "no line of the file are removed and a pseudonym the file "
                "gives otherwise is changed (the preview warns of both, and "
                "the backup keeps the list as it was), the longest real name "
                "comes first, and a pseudonym holding a backslash, which an "
                "earlier list may have and `prepare_names_list` copies into "
                "the file as a line, is refused until you change it in the "
                "file.") in upgrading
        assert upgrading.index("A names file stays with the project") < \
            upgrading.index("Saving the names list replaces") < \
            upgrading.index("Not in this release")
        assert "—" not in part and "better than QualCoder" not in part
        brief = _flat(unreleased)
        assert ("its section on how changes happen names importing "
                "documents, saving the names list and correcting the "
                "researcher's coder name among") in brief

    def test_the_measurement_names_its_entry(self):
        log = _flat(_read("CHANGELOG.md"))
        measured = log[log.index("### Measured"):log.index(
            "## [0.14.3-alpha]")]
        assert ("And `save_names_list`, which saves the names file as the "
                "list, adds its entry and its separator: 1,294 characters in "
                "`full`, 1,358 on 3.11; `core` does not serve it. No other "
                "tool's entry changed.") in measured
        assert "eighteen changes moved them" in measured
        server._apply_toolset("full")
        tool = next(t for t in asyncio.run(server.mcp.list_tools())
                    if t.name == "save_names_list")
        entry = len(json.dumps({"name": tool.name,
                                "description": tool.description or "",
                                "inputSchema": tool.inputSchema}))
        if sys.version_info[:2] == (3, 13):
            assert entry + len(", ") == 1294
        elif sys.version_info[:2] == (3, 11):
            assert entry + len(", ") == 1358
        brief = len(server.read_brief())
        assert f"the full brief {brief:,}." in measured

    def test_privacy_says_what_the_save_reads_and_writes(self):
        privacy = _flat(_read("PRIVACY.md"))
        assert ("When a names file is already there, `prepare_names_list` "
                "reads it for counts only") in privacy
        assert ("When you say the list is ready, `save_names_list` reads "
                "the file to check it: its preview gives counts, which "
                "compare the list with the file in the same way, and the "
                "numbers of the lines to correct, never a name; on your "
                "word, after a backup, it replaces the list in "
                "`pseudonyms.json` with the file's names, keeping only the "
                "list's entries the file cannot hold as a line, and the file "
                "itself stays as it is.") in privacy

    def test_install_names_it_among_the_tools_carrying_the_mark(self):
        install = _flat(_read("INSTALL.md"))
        assert ("mark Codex does not read (`import_documents` and "
                "`save_names_list` carry it too).") in install
        # fix round 1: the three marked tools in Claude Code's bullet, and
        # Codex asking before the save, which changes what exists
        assert ("a tool marked `anthropic/requiresUserInteraction` (here, "
                "`read_pseudonym_list`, `import_documents` and "
                "`save_names_list`) is asked about in every one of these "
                "modes but `dontAsk`, which refuses it.") in install
        assert ("`save_names_list` is also marked as changing what exists, "
                "so Codex asks before it under `auto` too.") in install
        marked = sorted(name for name, meta in server.TOOL_META.items()
                        if meta.get("anthropic/requiresUserInteraction"))
        assert marked == ["import_documents", "read_pseudonym_list",
                          "save_names_list"]

    def test_tools_says_what_3_8_2_does_with_such_names(self):
        tools = _flat(_read("TOOLS.md"))
        assert ("the names list is applied with each name written "
                "literally, where 3.8.2 read it as a pattern: there a real "
                "name holding a bracket, a question mark or another sign a "
                "pattern reads, or beginning or ending with a character "
                "that is not a letter or a digit, may be left in the text, "
                "stop the import, or replace other words; "
                "`save_names_list`'s preview warns of such names by line "
                "number.") in tools

    def test_ci_runs_the_qualcoder_check_in_the_parity_job(self):
        ci = _read(".github/workflows/ci.yml")
        job = ci[ci.index("  qualcoder-parity:"):]
        job = job[:job.index("\n  # ", 5)]
        assert "tests/test_v0150_save_names_list_qualcoder.py" in job
