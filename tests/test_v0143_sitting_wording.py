# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: two wording fixes from the maintainer's sitting with the test
build (transcripts of 10 and 11 October 2026).

The researcher's coder name. create_project asked for it "(in
QualCoder: Settings, Coder name)", but QualCoder 4.0's Settings window
labels it "Current coder" (`src/qualcoder/GUI/ui_dialog_settings.py`,
the label `label_current_coder`, at the tag 4.0; the window opens from
Project, Settings, which Qt moves to the QualCoder menu on a Mac). The
question also presumed QualCoder: a researcher who does not use it was
sent to `coder_name_not_known`, which leaves the check that keeps the
AI's codings apart from theirs off. Now the question asks what name the
researcher's own codings should carry: the name in QualCoder's settings
("Current coder"), exactly as there, for a QualCoder user, any name they
choose otherwise; `coder_name_not_known` stays for a researcher who does
not know it.

The folder for projects. In the sitting the assistant announced that
the project would go to ~/Documents/Exegete projects, the folder named
in create_project's description as the default, and the project went to
~/QualCoder projects, the desktop extension's "Folder for projects".
The folder that is set is now visible before a project is made:
list_available_projects, get_current_project and create_project (its
refusals too, so the question for the coder name carries it) give it as
`projects_folder`, and create_project, copy_project_to_workspace and
import_text_file name "the folder set for projects" rather than a
default, each description no longer than before
(tests/test_v0142_description_cut.py pins their words).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import database  # noqa: E402

OLD_LABEL = "Coder name)"
OLD_PATH = "Settings, Coder name"
LABEL = '("Current coder")'
STANDARD = "~/Documents/Exegete projects"


@pytest.fixture(autouse=True)
def _restore_selection():
    """Put the server's selected project back after each test, closing
    whatever a creation selected (an open handle keeps Windows from
    removing tmp_path)."""
    saved = (server.db, server.current_project_path)
    yield
    if server.db is not None and server.db is not saved[0]:
        try:
            server.db.close()
        except Exception:
            pass
    server.db, server.current_project_path = saved


@pytest.fixture
def projects_folder(tmp_path, monkeypatch):
    """A folder for projects set as the desktop extension sets it, away
    from the standard one."""
    folder = tmp_path / "QualCoder projects"
    folder.mkdir()
    monkeypatch.setenv("EXEGETE_WORKSPACE", str(folder))
    return folder


def _descriptions():
    server._apply_toolset("lifecycle")
    return server.mcp.original_descriptions


def _flat(text):
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# The researcher's coder name
# ---------------------------------------------------------------------------

class TestTheCoderNameQuestion:

    def test_the_question_names_qualcoder_40s_label(self):
        answer = json.loads(server.create_project("Study"))
        assert answer["success"] is False and answer["created"] is False
        assert answer["action_required"] == "ask_researcher_coder_name"
        text = answer["error"]
        assert LABEL in text, text
        assert OLD_LABEL not in text and OLD_PATH not in text

    def test_the_question_does_not_presume_qualcoder(self):
        text = json.loads(server.create_project("Study"))["error"]
        assert text.startswith(
            "Ask the researcher what name their own codings should carry; "
            "if they use QualCoder, the name in its settings "
            '("Current coder"), exactly as there; if not, any name they '
            "choose."), text
        # A researcher without QualCoder chooses a name; the flag is for
        # one who does not know it
        assert "do not use QualCoder" not in text
        assert "If they do not know it, call again with " \
               "coder_name_not_known=true instead." in text
        assert "never be guessed" in text

    def test_the_flag_still_creates_the_project(self, projects_folder):
        answer = json.loads(server.create_project(
            "Study", coder_name_not_known=True))
        assert answer["created"] is True, answer
        assert answer["coder_name_known"] is False

    def test_the_description_asks_the_same_question(self):
        d = _flat(_descriptions()["create_project"])
        assert ("THE RESEARCHER'S CODER NAME: ask the researcher what name "
                "their own codings should carry; if they use QualCoder, the "
                'name in its settings ("Current coder"), exactly as there; '
                "if not, any name they choose.") in d
        assert "If they do not know it, pass coder_name_not_known=true" in d
        assert "do not use QualCoder" not in d

    def test_no_served_text_names_the_old_label(self):
        served = dict(_descriptions())
        served["CODER_NAME_ASK"] = server.CODER_NAME_ASK
        served["instructions"] = server.mcp.instructions or ""
        served["brief"] = server._brief()
        for name, text in served.items():
            flat = _flat(text)
            assert OLD_LABEL not in flat, name
            assert OLD_PATH not in flat, name


# ---------------------------------------------------------------------------
# The folder set for projects
# ---------------------------------------------------------------------------

class TestTheFolderSetForProjects:

    def test_the_listing_gives_it_when_nothing_is_found(
            self, projects_folder, tmp_path):
        empty = tmp_path / "nothing here"
        empty.mkdir()
        answer = json.loads(server.list_available_projects([str(empty)]))
        assert answer["projects"] == []
        assert answer["projects_folder"] == str(projects_folder)
        # and with the usual places
        answer = json.loads(server.list_available_projects())
        assert answer["projects_folder"] == str(projects_folder)

    def test_the_listing_gives_it_beside_the_projects(
            self, projects_folder, qualcoder_db_path):
        parent = str(Path(qualcoder_db_path).parent)
        answer = json.loads(server.list_available_projects([parent]))
        assert answer["project_count"] >= 1, answer
        assert answer["projects_folder"] == str(projects_folder)

    def test_the_standard_folder_when_none_is_set(self, tmp_path):
        answer = json.loads(server.list_available_projects())
        standard = database.standard_workspace()
        assert answer["projects_folder"] == str(standard)
        # the sandbox's home, never the researcher's
        assert standard.resolve().is_relative_to(tmp_path.resolve())

    def test_get_current_project_gives_it_with_no_project(
            self, projects_folder):
        server.db, server.current_project_path = None, None
        answer = json.loads(server.get_current_project())
        assert answer["current_project"] is None
        assert answer["projects_folder"] == str(projects_folder)

    def test_get_current_project_gives_it_with_a_project(
            self, projects_folder, setup_server):
        answer = json.loads(server.get_current_project())
        assert answer["current_project"]
        assert answer["projects_folder"] == str(projects_folder)

    def test_the_question_for_the_coder_name_carries_it(
            self, projects_folder):
        """The assistant can say where the project will go while it asks
        for the coder name, before anything is made."""
        answer = json.loads(server.create_project("Study"))
        assert answer["action_required"] == "ask_researcher_coder_name"
        assert answer["projects_folder"] == str(projects_folder)
        assert not (projects_folder / "Study.qda").exists()

    def test_a_created_project_names_it(self, projects_folder):
        answer = json.loads(server.create_project("Study",
                                                  coder_name="carol"))
        assert answer["created"] is True, answer
        assert answer["projects_folder"] == str(projects_folder)
        assert Path(answer["project_path"]).parent == projects_folder

    def test_the_descriptions_name_no_default(self):
        descriptions = _descriptions()
        for name in ("create_project", "copy_project_to_workspace",
                     "import_text_file"):
            d = _flat(descriptions[name])
            assert STANDARD not in d, name
            assert "the folder set for projects" in d, name
        create = _flat(descriptions["create_project"])
        assert "get_current_project's projects_folder" in create
        assert "leave it out for the folder set for projects" in create
