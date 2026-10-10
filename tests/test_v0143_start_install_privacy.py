# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the README, INSTALL.md and PRIVACY.md on bringing documents
in and reading them.

The README's features and "Start here" mention both; INSTALL.md says
which formats need the optional part (PDF and EPUB), that the Claude
Desktop extension switches it on, and its licence (the AGPL, as
pyproject.toml and NOTICE say); PRIVACY.md says what a reading page
holds and where it is written, the places being the ones the code uses.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import reading_folder  # noqa: E402


def _flat(name: str) -> str:
    text = (REPO / name).read_text(encoding="utf-8")
    return " ".join(text.replace("\n>", " ").split())


def _between(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


def test_the_readmes_features_name_importing_and_reading():
    features = _between(_flat("README.md"), "## What you can do",
                        "## How it works")
    assert "**Bring in transcripts** as documents from your computer" \
        in features
    assert "or by you on a page in your browser." in features


def test_start_here_names_importing_a_file_and_reading_it():
    start = _between(_flat("README.md"), "## Start here",
                     "## Three commitments")
    assert ("then bring in your page: paste it, as in the example, or save "
            "it as a Word or text file and give the assistant its place, "
            "which keeps its text off the conversation.") in start
    assert "ask to open a file for reading" in start
    assert "Exegete opens a file for you to read with its coding " \
        "highlighted" in start


def test_install_says_which_formats_need_the_optional_part():
    install = _flat("INSTALL.md")
    section = _between(install, "### PDF and EPUB: the optional part",
                       "The step-by-step install below")
    assert "PDF and EPUB need an optional part, `pdf-epub`" in section
    assert ("The Claude Desktop extension switches it on by itself."
            ) in section
    for command in ('pip install "exegete[pdf-epub]"',
                    'pipx install "exegete[pdf-epub]"',
                    'uv tool install "exegete[pdf-epub]"'):
        assert command in section, command
    # the extension's own section points there
    extension = _between(install, "## Claude Desktop: the one-click",
                         "## Choosing your AI host")
    assert ("The extension switches on the optional part that reads PDF "
            "and EPUB documents") in extension


def test_install_gives_the_parts_licence_as_pyproject_and_notice_do():
    section = _between(_flat("INSTALL.md"),
                       "### PDF and EPUB: the optional part",
                       "The step-by-step install below")
    assert ("PyMuPDF and EbookLib are under the GNU Affero General Public "
            "License, version 3 (AGPL-3.0), so an install with this part "
            "is, taken as a whole, under the AGPL's terms") in section
    assert ("Exegete's own code stays under the LGPL (LGPL-3.0-or-later)"
            ) in section
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    part = re.search(r"(?ms)^pdf-epub = \[(.*?)^\]", pyproject).group(1)
    assert set(re.findall(r'"([a-z]+)[<>=]', part)) == {
        "pymupdf", "ebooklib", "lxml"}
    assert "Both are AGPL-3.0" in pyproject
    notice = _flat("NOTICE")
    assert ("adds PyMuPDF and EbookLib, both under the GNU Affero General "
            "Public License, version 3") in notice


def test_privacy_says_what_a_reading_page_holds_and_where(monkeypatch):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    privacy = _flat("PRIVACY.md")
    paragraph = _between(privacy, "**What a page holds, and where it is "
                         "written.**", "The page itself never reaches out")
    assert ("A reading page holds the file's whole text as stored, its "
            "codings") in paragraph
    assert "never into the project or the folder a document came from" \
        in paragraph
    home = Path("/home/someone")
    mac = reading_folder.root("darwin", home).relative_to(home)
    linux = reading_folder.root("linux", home).relative_to(home)
    assert f"`~/{mac.as_posix()}` on a Mac" in paragraph
    assert f"`~/{linux.as_posix()}` on Linux" in paragraph
    assert "`%LOCALAPPDATA%\\Exegete\\Reading` on Windows" in paragraph
