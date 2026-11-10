# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3: SUPPORT, CONTRIBUTING, the guide to choosing a project and
NOTICE, read in full. The facts their fix round corrected, each held to
its source.

- NOTICE names six only while the lock's EbookLib needs it. EbookLib
  0.20 requires lxml and six; 0.21, on PyPI since 1 November 2026 and
  in uv.lock from v0.15.4, requires lxml alone (PyPI's metadata for
  both, read on 4 November 2026), and nothing else in the lock needs
  six, so NOTICE no longer names it.
- CONTRIBUTING's map says that open_file_for_reading shows or opens a
  read-only copy of the original, never the original itself (reading.py;
  tests/test_v0143_reading.py, TestTheOriginal, holds the behaviour).
- SUPPORT's warnings about what an issue publishes: an issue is public;
  a line of the names file or of pseudonyms.json pairs a real name with
  its pseudonym; the host's log keeps every request and every answer.
  These safety sentences are the fact, so their words are held.
- CONTRIBUTING says that on Windows onnxruntime makes a few reports as
  it loads, before Exegete's switch can reach them
  (import_reading._onnxruntime_reports_off; PRIVACY.md, "How your data
  flows").
"""

import inspect
import re
import tomllib
from pathlib import Path

from exegete import private_files, reading
from exegete.database import PSEUDONYMS_JSON_NAME

REPO = Path(__file__).resolve().parents[1]
NOTICES = ("NOTICE", "packaging/pypi-old-name/NOTICE")


def _flat(name):
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def _lock_packages():
    return tomllib.loads(
        (REPO / "uv.lock").read_text(encoding="utf-8"))["package"]


def _libraries_section(notice):
    """NOTICE's paragraph on the libraries for document import, up to
    the account of what PyMuPDF 2 brings."""
    start = notice.index("Libraries for document import")
    return notice[start:notice.index("With Python 3.11 to 3.14 on ", start)]


def _sentence_with(text, words):
    at = text.index(words)
    start = max(text.rfind(". ", 0, at), text.rfind("; ", 0, at)) + 2
    end = text.find(". ", at)
    return text[start:end if end != -1 else len(text)]


def test_notice_names_six_with_the_ebooklib_release_that_needs_it():
    packages = _lock_packages()
    (ebooklib,) = [p for p in packages if p["name"] == "ebooklib"]
    needs = {d["name"] for d in ebooklib.get("dependencies", [])}
    # six comes with EbookLib alone: no other package in the lock needs it
    assert [p["name"] for p in packages
            if any(d["name"] == "six" for d in p.get("dependencies", []))
            ] == (["ebooklib"] if "six" in needs else [])
    assert (REPO / NOTICES[0]).read_bytes() == \
        (REPO / NOTICES[1]).read_bytes()
    section = _libraries_section(_flat(NOTICES[0]))
    assert "lxml (BSD-3-Clause), which EbookLib needs" in section
    # Any EbookLib release the paragraph gives by number is the lock's
    assert set(re.findall(r"EbookLib (\d+(?:\.\d+)+)", section)) == {
        ebooklib["version"]}
    if "six" in needs:
        sentence = _sentence_with(section, "six (MIT)")
        assert f"EbookLib {ebooklib['version']}" in sentence, sentence
    else:
        # The lock's EbookLib no longer needs six: NOTICE drops it
        assert not re.search(r"\bsix\b", section), section


def test_notice_names_what_lxmls_packages_contain():
    """lxml's LICENSES.txt, "Binary wheels": its packages contain zlib,
    iconv, libxml2, libxslt and libexslt (read in lxml 6.1.3's package
    for macOS on Apple silicon, 4 November 2026, whose etree module
    defines libiconv's, zlib's, libxml2's and libxslt's functions
    itself and links nothing but the system library)."""
    section = _libraries_section(_flat(NOTICES[0]))
    sentence = _sentence_with(section, "LICENSES.txt")
    for library in ("zlib (Zlib)", "iconv (LGPL-2.1)", "libxml2",
                    "libxslt", "libexslt (each MIT)"):
        assert library in sentence, library
    (lxml,) = [p for p in _lock_packages() if p["name"] == "lxml"]
    assert f"lxml {lxml['version']}" in sentence


def test_the_maps_line_for_reading_names_the_copy():
    """The two views besides the reading page act on a read-only copy of
    the original, written into the reading folder; the original itself
    is never shown or opened."""
    from exegete import server
    assert set(reading.SHOW_CHOICES) == {"reading_copy", "original",
                                         "in_folder"}
    assert inspect.signature(server.open_file_for_reading).parameters[
        "show"].default == "reading_copy"
    lines = [line for line in (REPO / "CONTRIBUTING.md").read_text(
        encoding="utf-8").splitlines() if "── reading.py " in line]
    assert len(lines) == 1, lines
    line = lines[0]
    assert "open_file_for_reading" in line
    assert "the reading page by default" in line
    assert "read-only copy of the original" in line
    assert "or the original in its folder" not in line


def test_support_warns_what_an_issue_and_a_log_publish():
    support = _flat("SUPPORT.md")
    assert ("An issue is public: anyone can read it, and search engines "
            "find it. Participants' data or a project put into an issue is "
            "published with it.") in support
    assert (f"A line of the names file, `{private_files.NAMES_FILE}`, or an "
            f"entry of the project's `{PSEUDONYMS_JSON_NAME}` pairs a real "
            f"name with its pseudonym.") in support
    assert ("a file that records every request to Exegete and every "
            "answer, the text of your documents included") in support
    assert ("Read a log before you copy any of it into an issue, and copy "
            "only the lines about the problem.") in support
    assert ("They include the request that failed and Exegete's answer, "
            "which can hold names, paths and quoted text") in support


def test_contributing_says_onnxruntime_reports_on_windows_as_it_loads():
    contributing = _flat("CONTRIBUTING.md")
    sentence = _sentence_with(contributing, "makes a few reports as it "
                              "loads")
    assert sentence.startswith("On Windows, onnxruntime"), sentence
    assert "before the switch can be reached" in sentence
    # The section of PRIVACY.md that the sentence names, which says what
    # those reports hold
    assert 'PRIVACY.md, "How your data flows"' in sentence
    assert "\n## How your data flows\n" in (REPO / "PRIVACY.md").read_text(
        encoding="utf-8")
