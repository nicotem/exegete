# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.3 (provisional), once 0.14.2 met the import and reading work:
the documents say what Exegete does now.

Bringing documents in (`import_documents`) and reading a whole file on
the researcher's screen (`open_file_for_reading`) are Exegete's from
0.14.3, so no document sends a researcher to QualCoder for them, and
the maps of the code name the modules that do them. The README's,
INSTALL.md's and the brief's own sentences are pinned where they were
pinned before (test_v0141_intro_openai.py, test_v0141_readme_review.py,
test_v014_release_fix1_texts.py, test_v0142_readme.py,
test_v0142_selfrep.py); this module holds the rest.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import exegete.server as server  # noqa: E402

DOCUMENTS = ("README.md", "INSTALL.md", "TOOLS.md", "AI_CODING_GUIDE.md",
             "QUICKSTART.md", "PRIVACY.md", "SUPPORT.md", "CLAUDE.md",
             "CONTRIBUTING.md")


def _flat(text):
    return " ".join(text.replace("\n>", " ").split())


def _read(name):
    return _flat((REPO / name).read_text(encoding="utf-8"))


def _manifest():
    return json.loads((REPO / "packaging" / "desktop-extension" /
                       "manifest.in.json").read_text(encoding="utf-8"))


def _served():
    texts = {name: _read(name) for name in DOCUMENTS}
    texts["the brief"] = _flat(server.BRIEF_FULL)
    texts["the extension's description"] = _flat(
        _manifest()["long_description"])
    return texts


def test_no_text_sends_documents_or_whole_files_to_qualcoder():
    """What 0.14.2 said Exegete did not do yet, in the words it used."""
    for where, text in _served().items():
        for words in ("documents other than text",
                      "imports only text",
                      "reading a whole file with its coding highlighted",
                      "reading a whole transcript yourself with its coding "
                      "highlighted",
                      "**Import transcripts**, link files to cases"):
            assert words not in text, (where, words)


def test_tools_md_names_both_ways_in_and_the_reading_page():
    tools = _read("TOOLS.md")
    assert ("- **Bring in documents** from the computer (provisional, "
            "v0.14.3: Word, OpenDocument, RTF, plain text, Markdown, web "
            "pages and subtitle files, and PDF and EPUB with the optional "
            "part) and **transcripts** through the conversation") in tools
    assert ("ask for the file to be opened for reading "
            "(`open_file_for_reading`, provisional: a page in your browser "
            "shows them in the text)") in tools
    # the tools those lines name
    for name in ("import_documents", "open_file_for_reading",
                 "import_text_file"):
        assert callable(getattr(server, name, None)), name


def test_the_coding_guide_offers_the_reading_page():
    guide = _read("AI_CODING_GUIDE.md")
    assert ("**You** read the coded passages back in the conversation, ask "
            "Claude to open the file for reading (provisional: a page in "
            "your browser shows them highlighted in the text, which stays "
            "off the conversation), or open the project in QualCoder to see "
            "them there") in guide


def test_the_extension_says_documents_come_in():
    assert ("bring in documents and transcripts, read them with their "
            "codings") in _manifest()["long_description"]


def test_the_maps_of_the_code_name_every_module():
    """CLAUDE.md sends agents to CONTRIBUTING.md for "the full map of
    src/exegete", so that map names every module; CLAUDE.md names the
    import's and the reading's own."""
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    tree = contributing[contributing.index("│   │   ├── __init__.py"):]
    tree = tree[:tree.index("```")]
    modules = sorted(p.name for p in (REPO / "src" / "exegete").glob("*.py"))
    missing = [name for name in modules if f"── {name}" not in tree]
    assert not missing, missing
    claude = _read("CLAUDE.md")
    assert "CONTRIBUTING.md (\"Project structure\") has the full map" in \
        claude
    for name in ("doc_import.py", "doc_readers.py", "import_reading.py",
                 "garbled_text.py", "reading.py", "reading_copy.py",
                 "reading_folder.py", "opener.py", "origin_mark.py",
                 "parts.py"):
        assert f"`{name}`" in claude, name
    assert "`import_*.py`" in claude
