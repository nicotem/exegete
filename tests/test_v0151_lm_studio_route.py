# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the LM Studio route: the README leads to INSTALL's recipe.

Asked on 20 October 2026 whether the install guidance is clear for LM
Studio users, the lead found the recipe reached only through INSTALL's
top, a thousand lines above it; the route table still saying a guide
for LM Studio was "considered on request"; the example project inside a
folder named after QualCoder; Step 1 installing without the part that
reads PDF and EPUB; nothing on how a researcher on `core`, which cannot
create a project, gets a first one; and a long aside on the sizes of
the tools' definitions in Step 3 (the owner's word of 20 October 2026,
ROADMAP_IDEAS, "the LM Studio route").

Pinned here, as facts: the README's "Other assistants" links straight
to the recipe's anchor, and INSTALL carries that anchor; the recipe has
the seven steps the README counts; the route table no longer sends LM
Studio readers to ask for a guide; Step 1 installs the part the code
needs for PDF and EPUB, in both of its forms; Step 5's example project
is where Exegete's own folder for projects is, named as create_project
names a project; the first project's paragraph rests on what `core`
leaves out; Step 3 states its sizes in one sentence. The sizes
themselves are held to the measurement in tests/test_toolset_modes.py.
"""

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

HEADING = "## LM Studio (fully local) (Experimental)"
ANCHOR = "lm-studio-fully-local-experimental"
INSTALL_ON_MAIN = "https://github.com/nicotem/exegete/blob/main/INSTALL.md"


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def _recipe():
    return _between(_read("INSTALL.md"), HEADING,
                    "## ChatGPT's desktop app and Codex (Experimental)")


def _links():
    spec = importlib.util.spec_from_file_location(
        "check_links", REPO / "scripts" / "check_links.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look their module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_readme_links_straight_to_the_recipe():
    other = _between(_flat(_read("README.md")), "**Other assistants.**",
                     "**Updating.**")
    # quoted as INSTALL's heading reads, so a search for it finds it
    # (test_v0150_renames_sets.py)
    assert (f"[INSTALL.md, \"LM Studio (fully local) (Experimental)\"]"
            f"({INSTALL_ON_MAIN}#{ANCHOR})") in other
    assert "has a recipe of its own in seven steps, with the `core` tool " \
           "set" in other
    # the paragraph still opens as it did (test_v0142_owner_decisions.py)
    assert other.startswith("**Other assistants.** Claude Code (not on "
                            "Claude's Free plan), LM Studio,")


def test_install_carries_that_anchor():
    links = _links()
    assert ANCHOR in links.anchors_of(_read("INSTALL.md"))
    assert _read("INSTALL.md").count(f"\n{HEADING}\n") == 1


def test_the_recipe_has_the_seven_steps_the_readme_counts():
    steps = re.findall(r"^\*\*Step (\d+)\.", _recipe(), re.MULTILINE)
    assert steps == [str(n) for n in range(1, 8)]


def test_the_route_table_no_longer_asks_for_a_guide_for_lm_studio():
    install = _flat(_read("INSTALL.md"))
    assert "considered on request" in install
    sentence = install[install.index("The recipes for OpenAI's apps"):]
    sentence = sentence[:sentence.index("GitHub Issues")]
    assert sentence == ("The recipes for OpenAI's apps and for LM Studio go "
                        "step by step; a guide of that kind for Claude Code "
                        "is considered on request: ask in [")
    assert "and LM Studio are considered on request" not in install


def test_step_1_installs_the_part_for_pdf_and_epub():
    from exegete import doc_readers, import_words
    recipe = _recipe()
    step = _between(recipe, "**Step 1.", "**Step 2.")
    assert 'pipx install "exegete[pdf-epub]"' in step
    assert ('python3 -m venv ~/exegete-venv && ~/exegete-venv/bin/pip '
            'install "exegete[pdf-epub]"') in step
    assert "pip install exegete\n" not in step
    assert "pipx install exegete\n" not in step
    assert ("Without that part, Exegete refuses to import PDF and EPUB "
            "files") in _flat(step)
    # the part is the one pyproject.toml declares, and without it the
    # import refuses exactly these two formats
    assert re.search(r"(?m)^pdf-epub = \[", _read("pyproject.toml"))
    assert doc_readers.OPTIONAL_FORMATS == frozenset(
        {doc_readers.PDF, doc_readers.EPUB})
    assert "cannot read PDF and EPUB files yet" in \
        import_words.FILE_REFUSALS["optional_missing"]
    # the section it points to is there
    assert "\n### PDF and EPUB: the optional part\n" in _read("INSTALL.md")


def test_step_5s_example_is_in_exegetes_folder_for_projects():
    from exegete import database, names
    # the Terminal route's folder for projects when EXEGETE_WORKSPACE is
    # not set
    assert database.standard_workspace().parts[-2:] == (
        "Documents", names.WORKSPACE_FOLDER)
    recipe = _recipe()
    folder = f"/Users/YOUR_USERNAME/Documents/{names.WORKSPACE_FOLDER}/"
    # create_project makes "<name>.qda" directly in the folder for
    # projects, so the example names the project as it would be made
    assert (f'"EXEGETE_PROJECT_PATH": "{folder}MyProject.qda"') in recipe
    assert "QualCoder_projects" not in recipe
    assert "QualCoder projects" not in recipe


def test_the_first_project_rests_on_what_core_leaves_out():
    from exegete import server
    assert "create_project" not in server.CORE_TOOLSET
    assert "import_documents" not in server.CORE_TOOLSET
    recipe = _flat(_recipe())
    first = recipe[recipe.index("**A first project.**"):]
    first = first[:first.index("**Step 6.")]
    assert first.startswith("**A first project.** `core` cannot create a "
                            "project or bring documents into one.")
    for words in ('with `full` in this entry (`"EXEGETE_TOOLSET": "full"`,',
                  "no `EXEGETE_PROJECT_PATH` line yet,",
                  "Step 4's 64k context",
                  # where create_project makes it on this route, and the
                  # setting that moves it (test_v014_desktop_extension.py)
                  "which makes it in `~/Documents/Exegete projects` unless "
                  "`EXEGETE_WORKSPACE` names another folder;",
                  "with the Claude Desktop extension (its conversation goes "
                  "to Anthropic);",
                  # never presume the researcher uses QualCoder
                  "or in QualCoder if you use it."):
        assert words in first, words
    # Step 4's figure for the full set is the one this paragraph names
    assert "or 64k if you must run the full surface" in recipe
    # it sits between Step 5 and Step 6
    assert recipe.index("**Step 5.") < recipe.index("**A first project.**") \
        < recipe.index("**Step 6.")


def test_step_3_states_its_sizes_in_one_sentence():
    recipe = _flat(_recipe())
    step = recipe[recipe.index("**Step 3."):recipe.index("**Step 4.")]
    sizes = step[step.index("Exegete offers"):
                 step.index("The full set exceeds")]
    assert sizes.count(". ") == 1 and sizes.rstrip().endswith(".")
    for gone in ("the 0.12 flagship", "accounts for about",
                 "novelty-filter", "idempotency", "docstring",
                 "five per cent", "mcp 1.30.0"):
        assert gone not in step, gone
