# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the AI coder name in Exegete's settings, given to each project
Exegete creates (ruling 73, item 6: "a filled-in name is used for new
projects without asking; empty means ask; projects with names are never
changed silently"). The coder names, piece 3 of 3, shape A: at creation.

Until 0.14.3 the setting (EXEGETE_AI_CODER_NAME, the extension's "AI
coder name") was a host's declaration: offered first when a project was
asked for its name, and asked about once when a project's name differed.
Now `create_project` stores it with the new project, without asking, and
says so; every other project is asked as before, the setting offered
first. What this file pins:

- the words that call the setting what it is: the extension's
  description, the ask's clause, the once-per-project question, the
  setter's warning, `export_refi_qda`'s description, the help topic and
  the brief's two lines;
- `create_project` with the setting: the name stored with its note and
  the setting acknowledged, the two files, the answer's field and first
  next step, and the first change writing under it with no question;
- "default", QualCoder's speaker coder and a file that cannot be written,
  each creating the project without a name and with its warning;
- without the setting, today's behaviour throughout;
- the documents that say so.
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                       # noqa: E402
from exegete import names, project_settings           # noqa: E402
from exegete.project_settings import (                # noqa: E402
    OLD_SIDECAR_NAME,
    SIDECAR_NAME,
    SidecarWriteError,
    read_sidecar,
)

AI, AI_OLD = names.SETTINGS["ai_coder_name"]
MARK = names.NEW_ONLY_SETTINGS["installed_as"]
TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))
PLACES = {
    "extension": "\"AI coder name\" in Exegete's settings (Settings, "
                 "Extensions, Exegete)",
    "terminal": "EXEGETE_AI_CODER_NAME in the host's configuration for "
                "Exegete",
}
ROUTES = sorted(PLACES)
SETTING = "Qwen 3.8 6bit"
SPEAKER = server.SPEAKER_SYSTEM_CODER


def _route(monkeypatch, route):
    if route == "extension":
        monkeypatch.setenv(MARK, "extension")
    else:
        monkeypatch.delenv(MARK, raising=False)
    return PLACES[route]


def _flat(text):
    return " ".join(text.split())


def _doc(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _restore_selection():
    """Put the selected project back after each test, closing whatever
    the test selected (an open handle keeps Windows from removing
    tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


def _create(name, tmp_path, **kwargs):
    folder = tmp_path / "here"
    folder.mkdir(exist_ok=True)
    kwargs.setdefault("coder_name", "carol")
    answer = json.loads(server.create_project(name, directory=str(folder),
                                              **kwargs))
    assert answer["created"] is True and answer["selected"] is True, answer
    return answer


def _ai_warnings(answer):
    """The answer's warnings about the AI coder name (a scratch folder's
    long path brings a warning of its own)."""
    return [w for w in answer["warnings"] if "AI coder name" in w]


def _owner_of_code(project_path, name):
    conn = sqlite3.connect(str(Path(project_path) / "data.qda"))
    try:
        row = conn.execute("SELECT owner FROM code_name WHERE name=?",
                           (name,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


# The first next step of a project created without an AI coder name, as
# it stood before this piece (the researcher's own name known)
ASK_STEP = (
    "No AI coder name is set for this project yet. Ask the researcher "
    "which name the AI's codings and other writes should be stored under, "
    "and call set_project_ai_coder_name before the first write that needs "
    "it; it must differ from the researcher's own coder name, \"carol\".")
STORED_STEP = (
    "The AI coder name is \"Qwen 3.8 6bit\", from Exegete's settings, "
    "stored with the project (exegete.json in the project folder) without "
    "asking; every row Exegete writes here carries it. Tell the "
    "researcher. Another name can be set for this project with "
    "set_project_ai_coder_name, on their word.")


# ---------------------------------------------------------------------------
# The words that call the setting what it is
# ---------------------------------------------------------------------------

# What the extension's description says, as facts (after 0.15.1 the page's
# descriptions were cut to plain statements: tests/test_v0151_settings_page.py)
AI_DESCRIPTION_SAYS = ("kept apart from yours",
                       "given to each project Exegete creates",
                       "Claude asks the first time a project needs it")

ASK_WITH_SETTING = (
    "No AI coder name is set for this project yet, so nothing was written. "
    "Ask the user which coder name this project's AI codings and other AI "
    "writes should be stored under, then call set_project_ai_coder_name "
    "with their answer and retry. The name is free text; a model name such "
    "as \"Qwen 3.8 6bit\" is a good choice, because codings by different "
    "models can then be compared later. Quick picks: \"AI Coding "
    "Assistant\" (Exegete's built-in default), \"Qwen 3.8 6bit\" (the AI "
    "coder name in Exegete's settings), or a name the researcher chooses "
    "(the model's name, for example). The name can be changed at any "
    "time with the same tool; earlier rows keep the name they were written "
    "under.")


def _mismatch(declared, current, place):
    return (
        f"The AI coder name in Exegete's settings is \"{declared}\", but "
        f"this project's AI coder name is \"{current}\". Nothing was "
        f"written. Ask the researcher which name to use here, then call "
        f"set_project_ai_coder_name with \"{declared}\" to switch the "
        f"project to it, or with \"{current}\" to keep it (that records the "
        f"choice, and Exegete will not ask again here while the setting, "
        f"{place}, stays the same). Earlier rows keep the name they were "
        f"written under.")


HELP_TOPIC = (
    "Rows Exegete writes carry the PROJECT's AI coder name, which the "
    "researcher chooses: in Exegete's settings, which give it to each "
    "project Exegete creates, or, in another project, when a write first "
    "needs it: that write stops and asks; relay the question, and call "
    "set_project_ai_coder_name with the user's answer. A model name is a "
    "good answer, because codings by different models can then be compared "
    "later with compare_coders. Never pick the name yourself.")


class TestTheWords:

    def test_the_extensions_description(self):
        option = TEMPLATE["user_config"]["ai_coder_name"]
        for words in AI_DESCRIPTION_SAYS:
            assert words in option["description"], words

    def test_the_ask_names_the_setting(self, setup_server_unset,
                                       monkeypatch):
        monkeypatch.setenv(AI, SETTING)
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITH_SETTING
        assert out["quick_picks"][0] == SETTING
        assert out["action_required"] == "set_project_ai_coder_name"

    @pytest.mark.parametrize("route", ROUTES)
    def test_the_once_per_project_question(self, setup_server_unset,
                                           qualcoder_db_path, monkeypatch,
                                           route):
        place = _route(monkeypatch, route)
        monkeypatch.delenv(AI, raising=False)
        server.set_project_ai_coder_name("Model A")
        monkeypatch.setenv(AI, "Model B")
        out = json.loads(server.create_code("Blocked", create_backup=False))
        assert out["error"] == _mismatch("Model B", "Model A", place)
        # its fields keep their names
        assert out["ai_coder_name"] == "Model A"
        assert out["host_declared_ai_coder_name"] == "Model B"
        assert out["quick_picks"] == ["Model B", "Model A"]
        assert _owner_of_code(qualcoder_db_path, "Blocked") is None
        # "keep": the project keeps its name, and is not asked again
        kept = json.loads(server.set_project_ai_coder_name("Model A"))
        assert kept["ai_coder_name"]["name"] == "Model A"
        out = json.loads(server.create_code("Kept", create_backup=False))
        assert out.get("success") is True, out
        assert _owner_of_code(qualcoder_db_path, "Kept") == "Model A"
        assert read_sidecar(Path(qualcoder_db_path)).name == "Model A"

    def test_the_import_preview_gives_the_same_question(
            self, setup_server_unset, monkeypatch):
        place = _route(monkeypatch, "terminal")
        monkeypatch.delenv(AI, raising=False)
        server.set_project_ai_coder_name("Model A")
        monkeypatch.setenv(AI, "Model B")
        assert server._import_owner_stop() == _mismatch("Model B", "Model A",
                                                        place)

    def test_the_setters_warning(self, setup_server_unset, monkeypatch):
        monkeypatch.delenv(AI, raising=False)
        server.set_project_ai_coder_name("Model A")
        monkeypatch.setenv(AI, "Model B")
        out = json.loads(server.set_project_ai_coder_name("Model A"))
        assert ("Unchanged; the choice was recorded again (acknowledging "
                "the AI coder name in Exegete's settings).") \
            in out["warnings"], out["warnings"]
        assert not any("declaration" in w for w in out["warnings"])

    def test_the_exports_description(self):
        text = _flat(server.mcp.original_descriptions["export_refi_qda"])
        assert ("The one export user is named after the project's AI coder "
                "name, else the AI coder name in Exegete's settings "
                "(EXEGETE_AI_CODER_NAME) or the built-in default; the result "
                "says which (ai_user_name_source).") in text
        assert "declaration" not in text

    def test_the_help_topic(self):
        overview = json.loads(server.explain_ai_coding_tools())
        assert overview["ai_coder_name"] == HELP_TOPIC

    def test_the_briefs_two_lines(self):
        for brief in (server.BRIEF_FULL, server.read_brief()):
            flat = _flat(brief)
            assert ("- Rows you write carry the project's AI coder name, "
                    "which the researcher chooses, in Exegete's settings or "
                    "when Exegete asks: relay Exegete's question; never "
                    "choose it yourself.") in flat
            assert "; and when Exegete asks for the AI coder name." in flat
            assert "when the AI coder name is needed" not in flat

    def test_create_projects_description(self):
        text = _flat(server.mcp.original_descriptions["create_project"])
        assert ("When the AI coder name is filled in Exegete's settings, the "
                "new project stores it too, and the answer says so.") in text


# ---------------------------------------------------------------------------
# create_project with the setting: shape A, at creation
# ---------------------------------------------------------------------------

class TestAtCreation:

    def test_the_new_project_takes_the_setting(self, tmp_path, monkeypatch):
        monkeypatch.setenv(AI, SETTING)
        answer = _create("Named", tmp_path)
        folder = Path(answer["project_path"])
        state = read_sidecar(folder)
        assert state.is_set and state.name == SETTING
        assert state.entry["note"] == (
            "Taken from Exegete's settings when the project was created.")
        assert state.entry["note"] == server.SETTINGS_NOTE
        # the setting is recorded as acknowledged, so the once-per-project
        # question never fires on it
        assert state.entry["host_declaration"] == SETTING
        assert answer["ai_coder_name"] == {"name": SETTING,
                                           "source": "settings"}
        assert answer["next_steps"][0] == STORED_STEP
        assert _ai_warnings(answer) == []
        # the fields the answer had keep theirs
        assert answer["coder_name"] == "carol"
        assert answer["coder_name_source"] == "given"

    # The two files creation writes beside the database with the setting
    # filled in, the named departure, are pinned beside
    # test_nothing_else_is_written in tests/test_v014_create_project.py.

    @pytest.mark.parametrize("tool", ["create_code", "import_text_file"])
    def test_the_first_change_writes_under_it_without_a_question(
            self, tmp_path, monkeypatch, tool):
        monkeypatch.setenv(AI, SETTING)
        folder = Path(_create("First", tmp_path)["project_path"])
        if tool == "create_code":
            out = json.loads(server.create_code("Theme",
                                                create_backup=False))
            assert out.get("success") is True, out
            assert _owner_of_code(folder, "Theme") == SETTING
        else:
            out = json.loads(server.import_text_file(
                "notes.txt", "Some words.", create_backup=False))
            assert out.get("success") is True, out
            conn = sqlite3.connect(str(folder / "data.qda"))
            try:
                owner = conn.execute(
                    "SELECT owner FROM source WHERE name='notes.txt'"
                ).fetchone()[0]
            finally:
                conn.close()
            assert owner == SETTING

    def test_a_changed_setting_asks_once_and_keeps_the_name(
            self, tmp_path, monkeypatch):
        """A project with a name is never changed silently: the setting
        changed after creation asks, as for any other project."""
        place = _route(monkeypatch, "extension")
        monkeypatch.setenv(AI, SETTING)
        folder = Path(_create("Later", tmp_path)["project_path"])
        monkeypatch.setenv(AI, "Model B")
        out = json.loads(server.create_code("Held", create_backup=False))
        assert out["error"] == _mismatch("Model B", SETTING, place)
        assert read_sidecar(folder).name == SETTING

    @pytest.mark.parametrize("route", ROUTES)
    @pytest.mark.parametrize("reserved,why", [
        ("default",
         "QualCoder reserves \"default\" for anyone who has not set a name"),
        (SPEAKER, "it is QualCoder's speaker coder"),
    ])
    def test_a_reserved_name_is_not_stored(self, tmp_path, monkeypatch,
                                           route, reserved, why):
        place = _route(monkeypatch, route)
        monkeypatch.setenv(AI, reserved)
        answer = _create("Reserved", tmp_path)
        folder = Path(answer["project_path"])
        assert _ai_warnings(answer) == [
            f"The AI coder name in Exegete's settings, \"{reserved}\", was "
            f"not stored: {why}. Ask the researcher for another "
            f"(set_project_ai_coder_name), and suggest changing {place}."]
        assert answer["ai_coder_name"] is None
        assert answer["next_steps"][0] == ASK_STEP
        assert not (folder / SIDECAR_NAME).exists()
        assert not (folder / OLD_SIDECAR_NAME).exists()
        assert not read_sidecar(folder).is_set

    def test_a_file_that_cannot_be_written_leaves_the_project(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv(AI, SETTING)

        def refuse(folder, name, **kwargs):
            try:
                raise PermissionError(13, "denied", str(folder))
            except PermissionError as error:
                raise SidecarWriteError(
                    "The AI coder name could not be stored with the project "
                    "(PermissionError). Nothing was changed.") from error

        monkeypatch.setattr(server, "store_ai_coder_name", refuse)
        answer = _create("Unwritten", tmp_path)
        assert answer["success"] is True
        assert _ai_warnings(answer) == [
            "The AI coder name in Exegete's settings, \"Qwen 3.8 6bit\", was "
            "not stored with the new project (PermissionError); the first "
            "change asks for it, with the setting offered first."]
        assert answer["ai_coder_name"] is None
        assert answer["next_steps"][0] == ASK_STEP
        assert (Path(answer["project_path"]) / "data.qda").is_file()
        # and the first change asks, with the setting offered first
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITH_SETTING

    def test_a_marker_that_cannot_be_written_is_tried_again(
            self, tmp_path, monkeypatch):
        """The name is stored; the earlier file's marker, when it cannot
        be written, is logged and written by the next change, as for any
        first naming."""
        monkeypatch.setenv(AI, SETTING)
        real = project_settings._create_exclusively
        calls = []

        def fail_once(folder, target, encoded):
            calls.append(target.name)
            if len(calls) == 1:
                raise PermissionError(13, "denied")
            return real(folder, target, encoded)

        monkeypatch.setattr(project_settings, "_create_exclusively",
                            fail_once)
        answer = _create("Unmarked", tmp_path)
        folder = Path(answer["project_path"])
        assert answer["ai_coder_name"] == {"name": SETTING,
                                           "source": "settings"}
        assert _ai_warnings(answer) == []
        assert (folder / SIDECAR_NAME).is_file()
        assert not (folder / OLD_SIDECAR_NAME).exists()
        out = json.loads(server.create_code("Retried", create_backup=False))
        assert out.get("success") is True, out
        assert (folder / OLD_SIDECAR_NAME).is_file()
        assert calls == [OLD_SIDECAR_NAME, OLD_SIDECAR_NAME]

    def test_the_log_names_neither_the_name_nor_the_path(
            self, tmp_path, monkeypatch, caplog):
        monkeypatch.setenv(AI, "Distinctive Model 7")
        with caplog.at_level(logging.DEBUG):
            answer = _create("Logged", tmp_path)
        text = "\n".join(r.getMessage() for r in caplog.records)
        assert "The AI coder name in the settings was stored" in text
        assert "Distinctive Model 7" not in text
        assert str(tmp_path) not in text
        assert answer["ai_coder_name"]["name"] == "Distinctive Model 7"


# ---------------------------------------------------------------------------
# Without the setting: today's behaviour throughout
# ---------------------------------------------------------------------------

class TestWithoutTheSetting:

    @pytest.mark.parametrize("value", [None, "", "  ",
                                       "${user_config.ai_coder_name}"])
    def test_creation_stores_no_name_and_the_first_change_asks(
            self, tmp_path, monkeypatch, value):
        for name in (AI, AI_OLD):
            monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv(AI, value)
        answer = _create("Plain", tmp_path)
        folder = Path(answer["project_path"])
        assert answer["ai_coder_name"] is None
        assert answer["next_steps"][0] == ASK_STEP
        assert _ai_warnings(answer) == []
        assert sorted(p.name for p in folder.iterdir()) == [
            "ai_data", "audio", "data.qda", "documents", "images", "video"]
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["action_required"] == "set_project_ai_coder_name"
        assert "(the AI coder name in Exegete's settings)" not in out["error"]

    def test_a_project_made_elsewhere_is_asked_with_the_setting_first(
            self, setup_server_unset, qualcoder_db_path, monkeypatch):
        """Guard: a project Exegete did not create, with no AI coder
        name, is asked as before; nothing is stored by the setting."""
        monkeypatch.setenv(AI, SETTING)
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITH_SETTING
        assert not (Path(qualcoder_db_path) / SIDECAR_NAME).exists()


# ---------------------------------------------------------------------------
# Fix round 1: a setting the setter refuses is not offered, and the words
# name the spelling of the setting in use
# ---------------------------------------------------------------------------

CODER = names.NEW_ONLY_SETTINGS["coder_name"]
# The ask as it stands without the clause on the setting
ASK_WITHOUT_SETTING = ASK_WITH_SETTING.replace(
    ", \"Qwen 3.8 6bit\" (the AI coder name in Exegete's settings)", "")
TERMINAL_OLD = f"{AI_OLD} in the host's configuration for Exegete"


class TestARefusedSettingIsNotOffered:
    """A setting set_project_ai_coder_name refuses in any project
    (QualCoder's "default", its speaker coder, the researcher's own coder
    name in the settings) is left out of the ask's words and quick picks:
    creation has just warned "Ask the researcher for another"."""

    def test_the_ask_without_the_clause_is_the_ask(self):
        assert ASK_WITHOUT_SETTING != ASK_WITH_SETTING
        assert "Exegete's settings" not in ASK_WITHOUT_SETTING

    @pytest.mark.parametrize("refused", ["default", SPEAKER, "Ann Lee"])
    def test_the_ask_leaves_it_out(self, setup_server_unset, monkeypatch,
                                   refused):
        monkeypatch.setenv(AI, refused)
        if refused == "Ann Lee":
            monkeypatch.setenv(CODER, "Ann Lee")
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITHOUT_SETTING
        # v0.15.0, piece 12: "AI Agent" only on its sign
        assert out["quick_picks"] == [server.DEFAULT_AI_CODER_NAME]
        # the import's preview gives the same ask
        assert server._import_owner_stop() == ASK_WITHOUT_SETTING
        # and the setter does refuse it
        refused_answer = json.loads(server.set_project_ai_coder_name(refused))
        assert refused_answer["error"].endswith("Nothing was changed.")
        assert not read_sidecar(Path(setup_server_unset.current_project_path)
                                ).is_set

    @pytest.mark.parametrize("refused", ["default", SPEAKER, "Ann Lee"])
    def test_rows_under_it_are_not_offered_as_the_ais(
            self, setup_server_unset, qualcoder_db_path, monkeypatch,
            refused):
        """Rows under such a name are a person's, or QualCoder's speaker
        codings: the ask does not propose continuing them as the AI's."""
        con = sqlite3.connect(str(Path(qualcoder_db_path) / "data.qda"))
        con.execute("INSERT INTO code_name (cid,name,memo,catid,owner,date,"
                    "color) VALUES (90,'Theirs','',NULL,?,'2024-01-15',"
                    "'#FF0000')", (refused,))
        con.commit()
        con.close()
        server.db.close()
        server.db = server.QualcoderDatabase(qualcoder_db_path)
        monkeypatch.setenv(AI, refused)
        if refused == "Ann Lee":
            monkeypatch.setenv(CODER, "Ann Lee")
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITHOUT_SETTING
        assert out["existing_ai_coder_names_in_project"] == []
        # v0.15.0, piece 12: "AI Agent" only on its sign
        assert out["quick_picks"] == [server.DEFAULT_AI_CODER_NAME]

    @pytest.mark.parametrize("reserved", ["default", SPEAKER])
    def test_after_creation_the_first_change_does_not_offer_it(
            self, tmp_path, monkeypatch, reserved):
        monkeypatch.setenv(AI, reserved)
        answer = _create("Reserved", tmp_path)
        assert answer["ai_coder_name"] is None
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITHOUT_SETTING
        assert reserved not in out["quick_picks"]

    def test_the_researchers_own_setting_alone_is_offered(
            self, setup_server_unset, monkeypatch):
        """Guard: the researcher's own setting keeps the AI setting out
        only when the two are the same name."""
        monkeypatch.setenv(CODER, "Ann Lee")
        monkeypatch.setenv(AI, SETTING)
        out = json.loads(server.create_code("Asked", create_backup=False))
        assert out["error"] == ASK_WITH_SETTING
        assert out["quick_picks"][0] == SETTING


class TestTheSpellingInUse:
    """Installed any other way than as the extension, the words name the
    AI coder name's variable as it is set: the earlier spelling when only
    that is set (read until v1.0), as the once-per-project question named
    it before v0.15.0; the new one otherwise."""

    @pytest.mark.parametrize("given,named", [
        ({AI: "Model B"}, AI),
        ({AI_OLD: "Model B"}, AI_OLD),
        ({AI: "Model B", AI_OLD: "Model B"}, AI),
        ({}, AI),
    ])
    def test_the_place(self, monkeypatch, given, named):
        _route(monkeypatch, "terminal")
        for name, value in given.items():
            monkeypatch.setenv(name, value)
        assert server._settings_place("ai") == (
            f"{named} in the host's configuration for Exegete")
        assert server._settings_place("both") == (
            f"EXEGETE_CODER_NAME or {named} in the host's configuration "
            f"for Exegete")
        assert server._settings_place("coder") == (
            "EXEGETE_CODER_NAME in the host's configuration for Exegete")
        # the extension names its own setting, whatever the spelling
        _route(monkeypatch, "extension")
        assert server._settings_place("ai") == PLACES["extension"]

    def test_the_once_per_project_question(self, setup_server_unset,
                                           monkeypatch):
        _route(monkeypatch, "terminal")
        server.set_project_ai_coder_name("Model A")
        monkeypatch.setenv(AI_OLD, "Model B")
        out = json.loads(server.create_code("Blocked", create_backup=False))
        assert out["error"] == _mismatch("Model B", "Model A", TERMINAL_OLD)

    def test_the_warning_for_a_reserved_name(self, tmp_path, monkeypatch):
        _route(monkeypatch, "terminal")
        monkeypatch.setenv(AI_OLD, "default")
        answer = _create("Reserved", tmp_path)
        assert _ai_warnings(answer) == [
            "The AI coder name in Exegete's settings, \"default\", was not "
            "stored: QualCoder reserves \"default\" for anyone who has not "
            "set a name. Ask the researcher for another "
            f"(set_project_ai_coder_name), and suggest changing "
            f"{TERMINAL_OLD}."]


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

class TestTheDocuments:

    def test_install(self):
        text = _doc("INSTALL.md")
        assert ("**AI coder name**: empty by default. It is the name "
                "Claude's work in your projects is stored under, so that it "
                "stays apart from yours; a model's name lets codings by "
                "different models be compared later. Filled in, Exegete "
                "gives it to each project it creates, without asking, and "
                "says so, and offers it first when another project needs "
                "one; left empty, Claude asks the first time a project "
                "needs it. A project that already has an AI coder name "
                "keeps it, and Claude asks you once whether to switch.") \
            in text
        assert ("- `EXEGETE_AI_CODER_NAME`: the AI coder name in Exegete's "
                "settings. The name that rows actually carry is each "
                "PROJECT's own (see \"Choosing the AI coder name\" in "
                "TOOLS.md). Set, it is given by `create_project` to each "
                "project it makes, without asking, and the answer says so "
                "(`ai_coder_name`, with the source `settings`)") in text
        assert ("Up to 0.14.3 it was offered first and checked against a "
                "project's own AI coder name, but never stored by itself.") \
            in text
        assert "it was only offered as the first quick pick" not in text
        assert ("`default` and QualCoder's speaker coder are never stored as "
                "an AI coder name: a new project is then made without one, "
                "and its answer says why; nor are they, or your own coder "
                "name, offered when a project is asked for one.") in text
        assert ("give the model the host runs, and every project Exegete "
                "creates from that host takes that name, and any other "
                "project without one is offered it first") in text
        assert "DECLARATION" not in text
        assert "Left empty, Claude still asks" not in text

    def test_tools(self):
        text = _doc("TOOLS.md")
        assert ("You can also choose it in advance, in Exegete's settings: "
                "the desktop extension's \"AI coder name\", or "
                "`EXEGETE_AI_CODER_NAME` in Exegete's `env` block on any "
                "other route:") in text
        assert ("Filled in, Exegete gives it to each project it creates, "
                "without asking, and `create_project`'s answer says so "
                "(`ai_coder_name`, with the source `settings`)") in text
        assert ("A project that already has an AI coder name keeps it: if "
                "it differs from the setting, the next write asks once which "
                "of the two to use rather than re-attributing anything") \
            in text
        assert ("stores the AI coder name in Exegete's settings with the "
                "new project when it is filled in, without asking, and says "
                "so (`ai_coder_name`, and the first of the next steps), so "
                "the project folder then also holds `exegete.json` and the "
                "earlier file `qualcoder_mcp.json`, written already marked "
                "as moved so that copies of Exegete from before its rename "
                "refuse to write the project; QualCoder reads neither;") \
            in text
        assert "Left empty, each project is asked." in text
        assert ("with the note \"Taken from Exegete's settings when the "
                "project was created.\" A project made another way") in text
        assert "DECLARATION by this host" not in text

    def test_privacy(self):
        text = _doc("PRIVACY.md")
        assert ("You can choose it in advance, in Exegete's settings (\"AI "
                "coder name\" in the extension, `EXEGETE_AI_CODER_NAME` on "
                "other routes): Exegete stores it with each project it "
                "creates, without asking, and the answer that creates the "
                "project says so.") in text
        assert ("When the AI coder name is filled in Exegete's settings, it "
                "is stored with the new project too, in `exegete.json`, "
                "beside `qualcoder_mcp.json`, the file of Exegete's earlier "
                "name,") in text
        assert "Left empty, no `exegete.json` is written." in text
        # what exegete.json holds, as the list of what Exegete keeps says
        assert ("an optional note (one you typed, for example the host and "
                "model version, or Exegete's own when the name came from its "
                "settings at creation), and the AI coder name in Exegete's "
                "settings at the time.") in text
        assert ("It is returned into the conversation by create_project when "
                "it stores the name, get_current_project, select_project and "
                "set_project_ai_coder_name") in text
        assert "declared in the host's server configuration" not in text
        assert "nothing else: no backup, no `exegete.json`" not in text
        assert "setting declares a name" not in text

    def test_readme_and_the_guides(self):
        assert ("Before its first write, it asks for the AI coder name, kept "
                "per project, under which Exegete writes what is done "
                "through the conversation, unless the project was made while "
                "it was filled in Exegete's settings.") in _doc("README.md")
        guide = _doc("AI_CODING_GUIDE.md")
        assert ("which you choose: in Exegete's settings (\"AI coder name\" "
                "in the extension, `EXEGETE_AI_CODER_NAME` on other routes), "
                "which give it to each project Exegete creates, without "
                "asking, and say so;") in guide
        assert "only declares a name to offer first" not in guide
        assert ("which the researcher chooses in Exegete's settings, for "
                "the projects Exegete creates, or the first time a write "
                "needs it") in _doc("AI_CODING_WORKFLOW.md")

    def test_the_changelog(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = _flat(text[text.index("## [0.15.0-alpha]"):
                                text.index("## [0.14.3")])
        # one section for both coder names since the release preparation
        assert "### Your coder name and the AI coder name" in unreleased
        assert ("**The AI coder name in Exegete's settings is given to each "
                "new project without asking.**") in unreleased
        assert ("A project that already has an AI coder name keeps it, and "
                "when the setting differs the next write asks once which to "
                "use there") in unreleased
        assert ("written already marked as moved, so that copies of Exegete "
                "from before its rename (0.12 to 0.14) refuse to write the "
                "project. Up to 0.14.3 the setting was offered first and "
                "checked against a project's own AI coder name, but never "
                "stored by itself.") in unreleased
        assert ("A setting the setter would refuse (these two, or the "
                "researcher's own coder name in the settings) is not offered "
                "when a project is asked for its AI coder name.") in unreleased
        assert "**Empty means ask**" in unreleased
        # nine since the write tools' sentence (not presuming QualCoder,
        # piece 5) landed beside this piece, ten since the four
        # outcomes' sentence (piece 13), and eleven since the removals
        # moved to v0.15.1 (whole-branch review, round 1), and thirteen
        # since the second round's notes and import_text_file's sentence,
        # and fourteen since get_current_project lists the files Exegete
        # keeps (the files design, piece 1), and fifteen since
        # restore_backup says a restore keeps the project's Exegete
        # folder (piece 2), and sixteen since the descriptions that gave
        # the lock file as QualCoder's alone name both of its causes (the
        # fourth reading of the documents), and seventeen since
        # prepare_names_list (the files design, piece 3), and eighteen
        # since save_names_list (piece 4), and nineteen since
        # read_pseudonym_list was removed (piece 5)
        assert ("on 3.13), nineteen changes moved them;") in unreleased
        assert ("And the AI coder name in the settings is given to each new "
                "project: `create_project`'s sentence on it grew its entry "
                "by 115 characters, 123 on 3.11, and `export_refi_qda`'s "
                "name for the setting, no longer \"this host's "
                "declaration\", by 17, 21 on 3.11; `core` serves neither.") \
            in unreleased
