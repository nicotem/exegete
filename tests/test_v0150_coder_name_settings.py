# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.0: the two coder names as settings, and the researcher's own
name taken from them when a project is made (ruling 73, item 6).

The owner, 11 October 2026: "It's not good to ask my username to be
typed in each time a new project is created, because that is prone to
error". Two settings, "Your coder name" (EXEGETE_CODER_NAME, one
spelling) and "AI coder name" (EXEGETE_AI_CODER_NAME and its earlier
spelling); a filled-in coder name is given to each project
create_project makes, without asking; empty means ask; a project that
has a name keeps it. What this file pins:

- the extension's two settings, their words and the variables they set;
- what "not set" means for both (missing, blank, an unfilled `${...}`);
- the start-up refusal of an invalid value, on each route, naming the
  setting and never the value;
- where each refusal sends the researcher (`_settings_place`);
- create_project with and without the setting, its notes and its three
  new refusals, each leaving nothing behind;
- the AI coder name setter's refusal of the settings' name;
- the notes a selection gives, each only when it applies.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server                       # noqa: E402
from exegete import (database, env_settings, names,     # noqa: E402
                     project_settings)

TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))
CODER = "EXEGETE_CODER_NAME"
AI, AI_OLD = names.SETTINGS["ai_coder_name"]
MARK = names.NEW_ONLY_SETTINGS["installed_as"]
EXTENSION_PLACES = {
    "coder": "\"Your coder name\" in Exegete's settings (Settings, "
             "Extensions, Exegete)",
    "ai": "\"AI coder name\" in Exegete's settings (Settings, Extensions, "
          "Exegete)",
    "both": "\"Your coder name\" or \"AI coder name\" in Exegete's settings "
            "(Settings, Extensions, Exegete)",
}
TERMINAL_PLACES = {
    "coder": "EXEGETE_CODER_NAME in the host's configuration for Exegete",
    "ai": "EXEGETE_AI_CODER_NAME in the host's configuration for Exegete",
    "both": "EXEGETE_CODER_NAME or EXEGETE_AI_CODER_NAME in the host's "
            "configuration for Exegete",
}
ROUTES = ["extension", "terminal"]


def _route(monkeypatch, route):
    if route == "extension":
        monkeypatch.setenv(MARK, "extension")
    else:
        monkeypatch.delenv(MARK, raising=False)
    return EXTENSION_PLACES if route == "extension" else TERMINAL_PLACES


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


def _here(tmp_path):
    """The folder each test makes its project in (the sandbox's home is
    beside it, in tmp_path)."""
    folder = tmp_path / "here"
    folder.mkdir(exist_ok=True)
    return folder


def _create(name, tmp_path, **kwargs):
    return json.loads(server.create_project(
        name, directory=str(_here(tmp_path)), **kwargs))


def _refused(answer):
    assert answer["success"] is False and answer["created"] is False, answer
    return answer["error"]


def _stored(answer):
    conn = sqlite3.connect(str(Path(answer["project_path"]) / "data.qda"))
    try:
        row = conn.execute("SELECT codername FROM project").fetchone()
        listed = [r[0] for r in conn.execute(
            "SELECT name FROM coder_names ORDER BY rowid")]
    finally:
        conn.close()
    return row[0], listed


def _nothing_made(tmp_path):
    assert list(_here(tmp_path).iterdir()) == []
    assert not database.default_workspace().exists()


# ---------------------------------------------------------------------------
# The extension's settings
# ---------------------------------------------------------------------------

CODER_DESCRIPTION = (
    "The name your own codings carry in a project, kept apart from the "
    "AI's. Filled in, Exegete gives it to each project it creates, without "
    "asking; left empty, Claude asks for it each time. Projects that "
    "already exist keep their coder name, or their lack of one. It must "
    "differ from the AI coder name. If you also use QualCoder, give the "
    "name in its settings (Current coder), exactly as there. At most 80 "
    "characters; a line break or tab, an invisible formatting character "
    "(the joiners some scripts need are allowed) or ##### stops the "
    "extension from starting.")
AI_DESCRIPTION = (
    "The name you would like Claude's work in a project stored under, so "
    "that it stays apart from yours; a model's name lets codings by "
    "different models be compared later. When a project has no AI coder "
    "name yet, Claude asks you for one the first time it needs it and "
    "offers this one first; when a project already has another, Claude "
    "asks you once which to use there. Left empty, Claude still asks. It "
    "must differ from your coder name. At most 80 characters; a line "
    "break or tab, an invisible formatting character (the joiners some "
    "scripts need are allowed) or ##### stops the extension from "
    "starting.")


class TestTheExtensionsSettings:

    @pytest.mark.parametrize("key,title,description", [
        ("coder_name", "Your coder name", CODER_DESCRIPTION),
        ("ai_coder_name", "AI coder name", AI_DESCRIPTION),
    ])
    def test_each_setting_and_its_words(self, key, title, description):
        option = TEMPLATE["user_config"][key]
        assert option == {"type": "string", "title": title,
                          "description": description, "default": "",
                          "required": False}

    def test_they_come_after_the_folder(self):
        assert list(TEMPLATE["user_config"]) == [
            "toolset", "projects_folder", "coder_name", "ai_coder_name",
            "update_check"]

    def test_the_variables_they_set(self):
        env = TEMPLATE["server"]["mcp_config"]["env"]
        assert env[CODER] == "${user_config.coder_name}"
        # both spellings of the AI coder name, so an earlier spelling
        # inherited from the environment cannot disagree
        assert env[AI] == env[AI_OLD] == "${user_config.ai_coder_name}"

    def test_the_long_description_names_them(self):
        assert TEMPLATE["long_description"].endswith(
            "The settings choose the tool set (every tool, or a smaller set "
            "for local models), the folder where new projects and working "
            "copies are kept, your coder name and the AI coder name, and "
            "whether Exegete tells you when a new version is out.")


class TestTheSettingsTable:

    def test_the_coder_name_has_one_spelling(self):
        assert names.NEW_ONLY_SETTINGS["coder_name"] == CODER
        assert project_settings.CODER_NAME_ENV == CODER
        assert CODER not in {n for pair in names.SETTINGS.values()
                             for n in pair}

    def test_its_raw_value_is_read_through_env_settings(self):
        assert env_settings.coder_name({}) is None
        assert env_settings.coder_name({CODER: "  Ann "}) == "  Ann "


# ---------------------------------------------------------------------------
# Not set
# ---------------------------------------------------------------------------

NOT_SET = [None, "", "   ", "${user_config.coder_name}",
           "  ${user_config.ai_coder_name} "]


class TestNotSet:

    @pytest.mark.parametrize("raw", NOT_SET)
    def test_the_researchers_setting(self, raw):
        environ = {} if raw is None else {CODER: raw}
        assert project_settings.settings_coder_name(environ) is None
        assert project_settings.settings_coder_name_problem(environ) is None

    @pytest.mark.parametrize("raw", NOT_SET)
    def test_the_ai_setting(self, raw, monkeypatch):
        environ = {} if raw is None else {AI: raw, AI_OLD: raw}
        assert project_settings.host_declaration(environ) is None
        for name, value in environ.items():
            monkeypatch.setenv(name, value)
        assert server._ai_coder_name() == server.DEFAULT_AI_CODER_NAME

    def test_a_value_is_stripped_and_kept(self):
        assert project_settings.settings_coder_name({CODER: " Ann Lee "}) \
            == "Ann Lee"
        assert project_settings.host_declaration({AI: " Qwen "}) == "Qwen"

    def test_an_invalid_researchers_value_reads_as_not_set(self):
        environ = {CODER: "Ann\nLee"}
        assert project_settings.settings_coder_name(environ) is None
        assert project_settings.settings_coder_name_problem(environ) == (
            "EXEGETE_CODER_NAME contains control characters (newlines, "
            "tabs or similar); a QualCoder coder name must be plain "
            "single-line text.")


# ---------------------------------------------------------------------------
# Start-up
# ---------------------------------------------------------------------------

# A value of each kind the validator refuses, with a word from it that
# the message must not repeat
INVALID = [
    ("Zebedee\nQuill", "control characters (newlines, tabs or similar)"),
    ("Zebedee​Quill", "invisible formatting characters"),
    ("Zebedee ##### Quill", "reserves as the private-memo marker"),
    ("Zebedee" + "q" * 80, "the maximum is 80"),
]


class TestStartUp:

    @pytest.fixture
    def stub_run(self, monkeypatch):
        calls = []
        monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
        monkeypatch.setattr(sys, "stdin", None)
        # no check for new versions from a test, on any route
        monkeypatch.setattr(server.updates, "start", lambda *a, **k: None)
        return calls

    def _start(self, monkeypatch, env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        try:
            server.main([])
        except SystemExit as exc:
            return exc.code
        return 0

    @pytest.mark.parametrize("route", ROUTES)
    @pytest.mark.parametrize("value,words", INVALID)
    def test_an_invalid_coder_name_stops_it(self, route, value, words,
                                            monkeypatch, capsys, stub_run,
                                            tmp_path):
        places = _route(monkeypatch, route)
        monkeypatch.setenv(database.WORKSPACE_ENV, str(tmp_path / "w"))
        assert self._start(monkeypatch, {CODER: value}) == 1
        err = capsys.readouterr().err
        problem = project_settings.settings_coder_name_problem({CODER: value})
        assert words in problem
        assert f"Error: {problem} Change {places['coder']}, or leave it " \
               f"empty to be asked for the name in each new project.\n" in err
        assert "Zebedee" not in err and "Quill" not in err
        assert stub_run == []

    @pytest.mark.parametrize("route", ROUTES)
    @pytest.mark.parametrize("value,words", INVALID)
    def test_an_invalid_ai_coder_name_stops_it(self, route, value, words,
                                               monkeypatch, capsys,
                                               stub_run, tmp_path):
        places = _route(monkeypatch, route)
        monkeypatch.setenv(database.WORKSPACE_ENV, str(tmp_path / "w"))
        assert self._start(monkeypatch, {AI: value, AI_OLD: value}) == 1
        err = capsys.readouterr().err
        try:
            database.validate_coder_name(value, AI)
        except ValueError as error:
            problem = str(error)
        assert words in problem
        assert f"Error: {problem} Change {places['ai']}, or leave it empty " \
               f"to be asked in each project that needs one.\n" in err
        assert "Zebedee" not in err and "Quill" not in err
        assert stub_run == []

    def test_the_example_as_the_extension_gives_it(self, monkeypatch,
                                                   capsys, stub_run):
        _route(monkeypatch, "extension")
        assert self._start(monkeypatch, {CODER: "Ann\nLee"}) == 1
        assert capsys.readouterr().err.splitlines()[-1] == (
            "Error: EXEGETE_CODER_NAME contains control characters "
            "(newlines, tabs or similar); a QualCoder coder name must be "
            "plain single-line text. Change \"Your coder name\" in "
            "Exegete's settings (Settings, Extensions, Exegete), or leave "
            "it empty to be asked for the name in each new project.")

    @pytest.mark.parametrize("raw", ["", "  ", "${user_config.ai_coder_name}"])
    def test_an_empty_or_unfilled_ai_name_starts(self, raw, monkeypatch,
                                                 capsys, stub_run, tmp_path):
        _route(monkeypatch, "extension")
        monkeypatch.setenv(database.WORKSPACE_ENV, str(tmp_path / "w"))
        assert self._start(monkeypatch, {AI: raw, AI_OLD: raw}) == 0, \
            capsys.readouterr().err
        assert stub_run == [{"transport": "stdio"}]

    @pytest.mark.parametrize("raw", ["", "  ", "${user_config.coder_name}"])
    def test_an_empty_or_unfilled_coder_name_starts(self, raw, monkeypatch,
                                                    capsys, stub_run,
                                                    tmp_path):
        _route(monkeypatch, "extension")
        monkeypatch.setenv(database.WORKSPACE_ENV, str(tmp_path / "w"))
        assert self._start(monkeypatch, {CODER: raw}) == 0, \
            capsys.readouterr().err
        assert stub_run == [{"transport": "stdio"}]

    def test_equal_names_and_qualcoders_names_do_not_stop_it(
            self, monkeypatch, capsys, stub_run, tmp_path):
        """Refused where used, so that the message reaches the
        conversation."""
        monkeypatch.setenv(database.WORKSPACE_ENV, str(tmp_path / "w"))
        for env in ({CODER: "Ann", AI: "Ann"},
                    {CODER: server.SPEAKER_SYSTEM_CODER},
                    {CODER: "default"}):
            stub_run.clear()
            assert self._start(monkeypatch, env) == 0, \
                capsys.readouterr().err
            assert stub_run == [{"transport": "stdio"}]
            for name in env:
                monkeypatch.delenv(name)


class TestTheSettingsPlace:

    @pytest.mark.parametrize("route", ROUTES)
    def test_three_forms_on_each_route(self, route, monkeypatch):
        places = _route(monkeypatch, route)
        for which in ("coder", "ai", "both"):
            assert server._settings_place(which) == places[which]


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------

SPARED = (" To be spared this question in later projects, the researcher can "
          "fill in {place}.")


class TestCreatingWithTheSetting:

    def test_the_setting_is_used_without_asking(self, monkeypatch,
                                                tmp_path):
        monkeypatch.setenv(CODER, "  Ann Lee ")
        answer = _create("Study", tmp_path)
        assert answer["created"] is True, answer
        assert answer["coder_name"] == "Ann Lee"
        assert answer["coder_name_known"] is True
        assert answer["coder_name_source"] == "settings"
        assert "coder_name_note" not in answer
        assert "action_required" not in answer
        assert _stored(answer) == (
            "Ann Lee", ["Ann Lee", server.SPEAKER_SYSTEM_CODER])
        assert server.CODER_NAME_NOT_KNOWN_WARNING not in answer["warnings"]

    def test_default_is_accepted(self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "default")
        answer = _create("Study", tmp_path)
        assert answer["coder_name"] == "default"
        assert answer["coder_name_source"] == "settings"

    def test_a_given_name_that_differs_is_used_with_a_note(
            self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        answer = _create("Study", tmp_path, coder_name="Bea Kim")
        assert answer["coder_name"] == "Bea Kim"
        assert answer["coder_name_source"] == "given"
        assert answer["coder_name_note"] == (
            "The researcher's own coder name in Exegete's settings is "
            "\"Ann Lee\"; this project records \"Bea Kim\", the name given "
            "for it.")
        assert _stored(answer)[0] == "Bea Kim"

    def test_a_given_name_that_is_the_setting_has_no_note(
            self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        answer = _create("Study", tmp_path, coder_name=" Ann Lee")
        assert answer["coder_name_source"] == "given"
        assert "coder_name_note" not in answer

    def test_a_given_name_without_the_setting_has_no_note(self, tmp_path):
        answer = _create("Study", tmp_path, coder_name="Bea Kim")
        assert answer["coder_name_source"] == "given"
        assert "coder_name_note" not in answer

    def test_not_known_with_the_setting(self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        answer = _create("Study", tmp_path, coder_name_not_known=True)
        assert answer["created"] is True
        assert answer["coder_name"] is None
        assert answer["coder_name_source"] == "not_known"
        assert answer["coder_name_note"] == (
            "The researcher's own coder name in Exegete's settings is "
            "\"Ann Lee\"; it was not used, because coder_name_not_known=true "
            "was passed, so this project records none.")
        assert server.CODER_NAME_NOT_KNOWN_WARNING in answer["warnings"]
        assert _stored(answer) == ("", [server.SPEAKER_SYSTEM_CODER])

    def test_not_known_without_the_setting(self, tmp_path):
        answer = _create("Study", tmp_path, coder_name_not_known=True)
        assert answer["coder_name_source"] == "not_known"
        assert "coder_name_note" not in answer

    def test_a_place_refusal_with_the_setting_asks_nothing(
            self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        answer = _create("bad|name", tmp_path)
        text = _refused(answer)
        assert "Before calling again" not in text
        assert "action_required" not in answer
        _nothing_made(tmp_path)


class TestCreatingWithoutTheSetting:

    @pytest.mark.parametrize("route", ROUTES)
    def test_the_question_says_where_to_fill_it_in(self, route,
                                                   monkeypatch, tmp_path):
        places = _route(monkeypatch, route)
        answer = _create("Study", tmp_path)
        text = _refused(answer)
        assert answer["action_required"] == "ask_researcher_coder_name"
        folder = _here(tmp_path) / "Study.qda"
        assert text == (server.CODER_NAME_ASK
                        + SPARED.format(place=places["coder"])
                        + f" The project will be made as '{folder}': tell "
                          f"the researcher when you ask.")
        _nothing_made(tmp_path)

    @pytest.mark.parametrize("route", ROUTES)
    def test_and_beside_a_place_refusal(self, route, monkeypatch, tmp_path):
        places = _route(monkeypatch, route)
        answer = _create("bad|name", tmp_path)
        text = _refused(answer)
        assert answer["action_required"] == "ask_researcher_coder_name"
        assert text.endswith(" Before calling again, also: "
                             + server.CODER_NAME_ASK
                             + SPARED.format(place=places["coder"]))
        _nothing_made(tmp_path)

    def test_an_unfilled_setting_still_asks(self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "${user_config.coder_name}")
        answer = _create("Study", tmp_path)
        assert answer["action_required"] == "ask_researcher_coder_name"
        _nothing_made(tmp_path)


class TestTheThreeRefusals:
    """Each through the path a coder-name problem takes, after the place
    checks, with nothing created, each ending "Nothing was created."."""

    @pytest.mark.parametrize("route", ROUTES)
    @pytest.mark.parametrize("arguments", [
        {}, {"coder_name": "Bea Kim"}, {"coder_name_not_known": True}])
    def test_two_settings_that_are_one_name(self, route, arguments,
                                            monkeypatch, tmp_path):
        places = _route(monkeypatch, route)
        monkeypatch.setenv(CODER, "Ann Lee")
        monkeypatch.setenv(AI, " Ann Lee")
        answer = _create("Study", tmp_path, **arguments)
        assert _refused(answer) == (
            "The researcher's own coder name and the AI coder name in "
            "Exegete's settings are both \"Ann Lee\". They must differ: AI "
            "codings stored under the researcher's own name could not be "
            "told apart from theirs. Ask the researcher to change one of "
            f"them ({places['both']}). Nothing was created.")
        assert "action_required" not in answer
        _nothing_made(tmp_path)

    @pytest.mark.parametrize("route", ROUTES)
    @pytest.mark.parametrize("own", [None, "Ann Lee"])
    def test_a_given_name_that_is_the_ai_setting(self, route, own,
                                                 monkeypatch, tmp_path):
        places = _route(monkeypatch, route)
        if own:
            monkeypatch.setenv(CODER, own)
        monkeypatch.setenv(AI_OLD, "Qwen 3")
        answer = _create("Study", tmp_path, coder_name="Qwen 3 ")
        assert _refused(answer) == (
            "The coder name given for the researcher, \"Qwen 3\", is also "
            "the AI coder name in Exegete's settings. They must differ: AI "
            "codings stored under the researcher's own name could not be "
            "told apart from theirs. Ask the researcher to change "
            f"{places['ai']}, or call again with another coder_name, as the "
            "researcher gives it. Nothing was created.")
        _nothing_made(tmp_path)

    @pytest.mark.parametrize("route", ROUTES)
    def test_the_speaker_coder_in_the_setting(self, route, monkeypatch,
                                              tmp_path):
        places = _route(monkeypatch, route)
        monkeypatch.setenv(CODER, server.SPEAKER_SYSTEM_CODER)
        answer = _create("Study", tmp_path)
        assert _refused(answer) == (
            f"Exegete's settings give \"{server.SPEAKER_SYSTEM_CODER}\" as "
            "the researcher's own coder name, but that is QualCoder's "
            "speaker coder, which every project lists; it is not a person's "
            "coder name. Ask the researcher to change "
            f"{places['coder']}, or call again with the researcher's own "
            "coder name as coder_name. Nothing was created.")
        _nothing_made(tmp_path)

    def test_a_refusal_rides_beside_a_place_refusal(self, monkeypatch,
                                                    tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        monkeypatch.setenv(AI, "Ann Lee")
        text = _refused(_create("bad|name", tmp_path))
        assert " Before calling again, also: The researcher's own coder " \
               "name and the AI coder name" in text
        _nothing_made(tmp_path)


def _flat(text):
    return " ".join(text.split())


class TestTheDescription:

    def test_the_coder_name_paragraph(self):
        # v0.15.0, the coder names, piece 2: the sentence on
        # set_project_coder_name (tests/test_v0150_coder_name_correction.py)
        server._apply_toolset("full")
        d = _flat(server.mcp.original_descriptions["create_project"])
        assert (
            "THE RESEARCHER'S CODER NAME: do not ask for it before the first "
            "call. Leave coder_name out: when the researcher has filled in "
            "their coder name in Exegete's settings, it is used without "
            "asking and the answer says so (coder_name_source); otherwise "
            "nothing is created and the answer gives the question to ask: "
            "what name their own codings should carry; if they use "
            "QualCoder, the name in its settings (\"Current coder\"), "
            "exactly as there; if not, any name they choose. It is their "
            "own name, not the AI's: take it only from the researcher or "
            "from Exegete's settings, and never guess it, since a wrong name "
            "makes QualCoder, if they use it, ask them to keep or switch "
            "names when they open the project. It can be corrected later "
            "with set_project_coder_name only while nothing is recorded "
            "under it, so ask for the name as they want it to stay. Pass "
            "coder_name only with a "
            "name the researcher gave; if they do not know it, pass "
            "coder_name_not_known=true instead: the project is then created "
            "without one, and the result says what that means. Names:") in d


# ---------------------------------------------------------------------------
# The AI coder name setter
# ---------------------------------------------------------------------------

class TestTheSetter:

    def test_the_settings_researcher_name_is_refused(self, monkeypatch,
                                                     tmp_path):
        _create("Study", tmp_path, coder_name="Bea Kim")
        monkeypatch.setenv(CODER, "Ann Lee")
        answer = json.loads(server.set_project_ai_coder_name(" Ann Lee "))
        assert answer == {"error": (
            "\"Ann Lee\" is the researcher's own coder name in Exegete's "
            "settings, so AI rows under it could not be told apart from "
            "theirs. Choose a different name. Nothing was changed.")}
        folder = Path(server.current_project_path)
        for name in ("exegete.json", "qualcoder_mcp.json"):
            assert not (folder / name).exists()
        # another name is stored
        answer = json.loads(server.set_project_ai_coder_name("Qwen 3"))
        assert answer["success"] is True

    def test_the_projects_own_name_is_refused_first(self, monkeypatch,
                                                    tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        _create("Study", tmp_path)
        answer = json.loads(server.set_project_ai_coder_name("Ann Lee"))
        assert answer["error"].startswith(
            "\"Ann Lee\" is this project's own coder name")

    def test_the_description_names_the_refusal(self):
        server._apply_toolset("full")
        d = _flat(server.mcp.original_descriptions[
            "set_project_ai_coder_name"])
        assert ("Refused if the name is the project's own coder name or the "
                "researcher's own coder name in Exegete's settings, "
                "QualCoder's literal default coder name \"default\", or "
                "QualCoder's speaker coder") in d


# ---------------------------------------------------------------------------
# What a selection says
# ---------------------------------------------------------------------------

def _notes_of_both(path):
    selected = json.loads(server.select_project(path))
    assert selected["success"] is True, selected
    current = json.loads(server.get_current_project())
    return selected.get("coder_name_notes"), current.get("coder_name_notes")


# v0.15.0, the coder names, piece 2: the first two end with what
# set_project_coder_name does (tests/test_v0150_coder_name_correction.py)
DIFFERS = (
    "This project's own coder name is \"Bea Kim\"; the researcher's own "
    "coder name in Exegete's settings is \"Ann Lee\", which Exegete gives "
    "only to the projects it creates from now on. A project's own coder "
    "name is never changed without the researcher's word. "
    "set_project_coder_name corrects it while nothing is recorded under "
    "it.")
NONE_RECORDED = (
    "This project records no coder name for the researcher, so the check "
    "of the AI coder name against the project's own coder name is off; the "
    "researcher's own coder name in Exegete's settings, \"Ann Lee\", is "
    "still refused as the AI coder name, and Exegete gives it only to the "
    "projects it creates from now on. set_project_coder_name gives it "
    "one.")
AI_IS_SETTING = (
    "This project's AI coder name is \"Ann Lee\", which is also the "
    "researcher's own coder name in Exegete's settings, so AI codings "
    "stored under it could not be told apart from theirs. Ask the "
    "researcher whether to change it with set_project_ai_coder_name; it "
    "is never changed without their word.")


class TestTheSelectionNotes:

    def test_a_project_under_another_name(self, monkeypatch, tmp_path):
        path = _create("Study", tmp_path, coder_name="Bea Kim")["project_path"]
        assert _notes_of_both(path) == (None, None)
        monkeypatch.setenv(CODER, "Ann Lee")
        assert _notes_of_both(path) == ([DIFFERS], [DIFFERS])

    def test_a_project_under_the_settings_name(self, monkeypatch, tmp_path):
        monkeypatch.setenv(CODER, "Ann Lee")
        path = _create("Study", tmp_path)["project_path"]
        assert _notes_of_both(path) == (None, None)

    def test_a_project_that_records_none(self, monkeypatch, tmp_path):
        path = _create("Study", tmp_path,
                       coder_name_not_known=True)["project_path"]
        assert _notes_of_both(path) == (None, None)
        monkeypatch.setenv(CODER, "Ann Lee")
        assert _notes_of_both(path) == ([NONE_RECORDED], [NONE_RECORDED])

    def test_a_null_name_records_none_too(self, monkeypatch, tmp_path):
        path = _create("Study", tmp_path,
                       coder_name_not_known=True)["project_path"]
        conn = sqlite3.connect(str(Path(path) / "data.qda"))
        with conn:
            conn.execute("UPDATE project SET codername = NULL")
        conn.close()
        monkeypatch.setenv(CODER, "Ann Lee")
        assert _notes_of_both(path) == ([NONE_RECORDED], [NONE_RECORDED])

    @pytest.mark.parametrize("route", ROUTES)
    def test_two_settings_that_are_one_name(self, route, monkeypatch,
                                            tmp_path):
        places = _route(monkeypatch, route)
        path = _create("Study", tmp_path, coder_name="Bea Kim")["project_path"]
        monkeypatch.setenv(CODER, "Ann Lee")
        monkeypatch.setenv(AI, "Ann Lee")
        equal = ("The researcher's own coder name and the AI coder name in "
                 "Exegete's settings are both \"Ann Lee\"; they must differ, "
                 "so a new project is refused until one is changed "
                 f"({places['both']}).")
        assert _notes_of_both(path) == ([DIFFERS, equal], [DIFFERS, equal])

    def test_no_notes_without_the_setting(self, monkeypatch, tmp_path):
        path = _create("Study", tmp_path, coder_name="Bea Kim")["project_path"]
        monkeypatch.setenv(AI, "Bea Kim")
        assert _notes_of_both(path) == (None, None)

    def test_an_ai_coder_name_that_is_the_setting(self, monkeypatch,
                                                  tmp_path):
        """A project whose AI coder name was set to the name the
        researcher later fills in as their own keeps it, and the selection
        says so; nothing is changed by saying it."""
        path = _create("Study", tmp_path, coder_name="Bea Kim")["project_path"]
        assert json.loads(server.set_project_ai_coder_name(
            "Ann Lee"))["success"] is True
        sidecar = Path(path) / "exegete.json"
        before = sidecar.read_bytes()
        assert _notes_of_both(path) == (None, None)
        monkeypatch.setenv(CODER, "Ann Lee")
        assert _notes_of_both(path) == ([DIFFERS, AI_IS_SETTING],
                                        [DIFFERS, AI_IS_SETTING])
        assert sidecar.read_bytes() == before
        # another name in the settings: no such note
        monkeypatch.setenv(CODER, "Cy Ode")
        selected, current = _notes_of_both(path)
        assert not any("AI coder name is" in n for n in selected + current)

    def test_and_in_a_project_that_records_none(self, monkeypatch,
                                                tmp_path):
        path = _create("Study", tmp_path,
                       coder_name_not_known=True)["project_path"]
        assert json.loads(server.set_project_ai_coder_name(
            "Ann Lee"))["success"] is True
        monkeypatch.setenv(CODER, "Ann Lee")
        assert _notes_of_both(path) == ([NONE_RECORDED, AI_IS_SETTING],
                                        [NONE_RECORDED, AI_IS_SETTING])


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

def _doc(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


class TestTheDocuments:

    def test_install_the_extensions_settings(self):
        install = _doc("INSTALL.md")
        assert "4. **Look at its settings** (Settings, Extensions, " \
               "Exegete)." in install
        assert "Look at its three settings" not in install
        assert ("- **Your coder name**: empty by default. It is the name "
                "your own codings carry in a project, kept apart from the "
                "AI's. Filled in, Exegete gives it to each new project it "
                "makes, without asking, and says so; left empty, Claude asks "
                "for it each time.") in install
        assert ("- **AI coder name**: empty by default. It is the name you "
                "would like Claude's work in a project stored under") \
            in install
        step = install[install.index("- **Your coder name**: empty"):
                       install.index("- **AI coder name**: empty")]
        assert ("Projects that already exist keep their coder name, or "
                "their lack of one.") in step
        assert ("At most 80 characters; a line break or tab, an invisible "
                "formatting character (the joiners some scripts need are "
                "allowed) or `#####` stops the extension from starting.") \
            in step
        assert "already has a coder name keeps it" not in install

    def test_install_the_variables(self):
        install = _doc("INSTALL.md")
        assert ("The desktop extension sets both spellings of these four "
                "settings itself (the tool set, the two for the workspace "
                "and the AI coder name), always to the same value.") \
            in install
        assert ("Four settings are new and have one spelling only: the two "
                "of the check for new versions (`EXEGETE_UPDATE_CHECK` and "
                "`EXEGETE_INSTALLED_AS`), `EXEGETE_CALL_SECONDS` and "
                "`EXEGETE_CODER_NAME`, all below.") in install
        assert "The two settings of the check for new versions," \
            not in install
        # "Exegete", not "the server", in the passages this piece edits
        assert ("Exegete still reads them until v1.0, and its log says once "
                "per start") in install
        assert "Exegete does not start, and says which two disagree" \
            in install
        assert "The server still reads them" not in install
        assert "the server does not start, and says which" not in install
        assert ("- `EXEGETE_CODER_NAME` (0.15.0): your own coder name, the "
                "name your own codings carry in a project, kept apart from "
                "the AI's. Set, it is given by `create_project` to each "
                "project it makes, without asking") in install
        assert ("Projects that already exist keep their coder name, or "
                "their lack of one: Exegete gives it only to the projects it "
                "creates from now on, and selecting a project that records "
                "another name, or none, or whose AI coder name is this one, "
                "says so (`coder_name_notes`).") in install
        assert "It never changes the coder name of a project" not in install
        # the AI coder name's entry
        assert "must be non-empty" not in install
        assert "Empty or unset, no name is offered first." in install
        assert ("An invalid value stops Exegete at start-up with \"Error: "
                "EXEGETE_AI_CODER_NAME ...\" on stderr. It must differ from "
                "your own coder name (`EXEGETE_CODER_NAME`, and each "
                "project's)") in install
        assert "Do not declare your own coder name" not in install

    def test_tools(self):
        tools = _doc("TOOLS.md")
        assert ("Takes the researcher's own coder name from Exegete's "
                "settings when it is filled in, and otherwise asks for it "
                "(or an explicit \"not known\") after every other check; "
                "the answer that creates the project says where the name "
                "came from (`coder_name_source`, with `coder_name_note` when "
                "the settings hold another name); refuses a coder name equal "
                "to the AI coder name in the settings, and every creation "
                "while the two settings hold one name;") in tools
        assert ("and `coder_name_notes` when a note on the researcher's own "
                "coder name in Exegete's settings applies") in tools
        assert "`coder_name_notes` as `select_project` gives them" in tools
        assert ("When it is set, the name cannot be your own coder name") \
            in tools
        assert ("apart again later. All three are refused, and so is "
                "QualCoder's speaker coder") in tools
        assert ("A project whose AI coder name was set before you filled in "
                "the same name as your own in Exegete's settings keeps it, "
                "since it is never changed silently, and selecting the "
                "project says so (`coder_name_notes`).") in tools
        assert ("- **Your coder name.** Exegete takes it from its settings "
                "when you have filled it in there") in tools
        assert ("refuses the researcher's own coder name (the project's, or "
                "the one in Exegete's settings)") in tools
        assert "Invalid values (empty," not in tools
        assert ("(the project's codername, which QualCoder also uses, or "
                "the one in Exegete's settings)") in tools

    def test_readme_and_privacy(self):
        assert ("the assistant asks for your own coder name, unless you have "
                "filled it in Exegete's settings;") in _doc("README.md")
        privacy = _doc("PRIVACY.md")
        item = privacy[privacy.index("- **Creating a project** "
                                     "(`create_project`"):]
        item = item[:item.index("## Your governance options")]
        assert ("The coder name is asked for, or taken from Exegete's own "
                "settings when the researcher has filled it in there, never "
                "read from QualCoder's:") in item
        assert ("Both coder name settings, the researcher's and the AI's, "
                "reach Exegete from the app that starts it") in item
        # one person through the passage, and "it" no longer ambiguous
        assert "you have filled it in" not in item
        assert "yours and the AI's" not in item
        assert ("To refuse a name already in use, `create_project` lists "
                "the target folder's entries") in item
        # the name in the settings still reaches the conversation
        assert ("A coder name in the settings still enters the "
                "conversation: `create_project`'s answers give it, and so do "
                "the notes a selection gives when they apply "
                "(`coder_name_notes`), for instance when the project records "
                "another name or none. A coder name that is not the "
                "researcher's real name works as well, for a researcher who "
                "would rather the AI provider did not see it.") in item
        assert ("A name that belongs to a person (the project's own coder "
                "name, or the one in Exegete's settings) is refused") \
            in privacy

    def test_quickstart(self):
        assert ("Exegete asks the assistant to check your coder name with "
                "you first (the name your own codings will carry) and to say "
                "where the project will be made, unless your coder name is "
                "already set (`EXEGETE_CODER_NAME` in the `env` section "
                "above, or \"Your coder name\" in the extension's settings): "
                "then the project is made with that name at once, and the "
                "answer says where.") in _doc("QUICKSTART.md")

    def test_the_changelog(self):
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = text[text.index("## [Unreleased]"):
                          text.index("## [0.14.3")]
        assert "### Added: your coder name and the AI coder name as " \
               "settings" in unreleased
        assert "### Changed: an empty AI coder name, and the names the " \
               "setter refuses" in unreleased
        flat = _flat(unreleased)
        assert ("**Projects that already exist keep their coder name, or "
                "their lack of one**: Exegete gives the setting's name only "
                "to the projects it creates from now on.") in flat
        assert ("and so does selecting one whose AI coder name is the name "
                "in the settings.") in flat
        assert ("(over 80 characters, a line break or tab, an invisible "
                "formatting character other than the joiners some scripts "
                "need, or `#####`)") in flat
        assert "which only projects Exegete creates take" not in flat
