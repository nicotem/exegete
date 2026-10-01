# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.3 (provisional): reading a whole file on the computer.

The reading tool, `open_file_for_reading`, writes a reading copy (a web
page with the whole text and its codings) into Exegete's private reading
folder and opens it in the researcher's browser, or opens or shows a
read-only copy of the original. What leaves the computer is the file id,
the page's place and counts, never the text or a memo: these tests hold
the answers to that. No window is ever opened: conftest's
`_no_window_opens` gives every test launchers that only record.
"""

import asyncio
import json
import os
import sqlite3
import stat
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import opener, reading_folder  # noqa: E402

# Words that appear only in the file's text and memos, so that an answer
# carrying any of them carries the text.
SECRET_TEXT = "Marigold"
SECRET_MEMO = "Quinceharbour"
PRIVATE_MEMO = "Tamarillo"
TEXT = (f"Opening line.\nI said {SECRET_TEXT} twice  with\ttabs.\n"
        f"Then 😀 an emoji and more words.\n\nThe end <script>x</script>")


def host(tool: str, **args):
    """Call a tool the way a host does and return its parsed JSON."""
    out = asyncio.run(server.mcp.call_tool(tool, args))
    if isinstance(out, tuple):
        out = out[0]
    if isinstance(out, dict):
        return out
    return json.loads("".join(getattr(b, "text", "") for b in out))


def raw(tool: str, **args) -> str:
    out = asyncio.run(server.mcp.call_tool(tool, args))
    if isinstance(out, tuple):
        out = out[0]
    return "".join(getattr(b, "text", "") for b in out)


def sql(project, query, args=()):
    conn = sqlite3.connect(str(Path(project) / "data.qda"))
    try:
        conn.execute(query, args)
        conn.commit()
    finally:
        conn.close()


def add_file(project, file_id, name, text, mediapath=None, memo=""):
    sql(project, "INSERT INTO source (id, name, fulltext, mediapath, memo, "
        "owner, date) VALUES (?, ?, ?, ?, ?, 'TestCoder', '2026-10-01')",
        (file_id, name, text, mediapath, memo))


def add_coding(project, ctid, cid, fid, start, end, text, memo="",
               important=0):
    sql(project, "INSERT INTO code_text (ctid, cid, fid, seltext, pos0, "
        "pos1, owner, date, memo, important) VALUES "
        "(?, ?, ?, ?, ?, ?, 'TestCoder', '2026-10-01', ?, ?)",
        (ctid, cid, fid, text, start, end, memo, important))


def units(text: str, index: int) -> int:
    """A character index as QualCoder's editor counts it (UTF-16)."""
    return len(text[:index].encode("utf-16-le")) // 2


@pytest.fixture
def project(setup_server):
    """The fixture project with file 50: the text above, two
    overlapping codings, one with a memo whose private part must stay
    out, one placed after the emoji by QualCoder's count, and an
    annotation."""
    folder = server._current_project_folder()
    add_file(folder, 50, "P03 interview.docx", TEXT,
             mediapath="/docs/P03 interview.docx",
             memo=f"About the file. ##### {PRIVATE_MEMO}")
    start = TEXT.index(SECRET_TEXT)
    add_coding(folder, 501, 1, 50, start, start + 20,
               TEXT[start:start + 20],
               memo=f"{SECRET_MEMO} ##### {PRIVATE_MEMO}", important=1)
    add_coding(folder, 502, 2, 50, start + 8, start + 30,
               TEXT[start + 8:start + 30])
    after = TEXT.index("an emoji")
    add_coding(folder, 503, 2, 50, units(TEXT, after),
               units(TEXT, after) + 8, "an emoji")
    sql(folder, "INSERT INTO annotation (anid, fid, pos0, pos1, memo, "
        "owner, date) VALUES (1, 50, 0, 7, ?, 'TestCoder', '2026-10-01')",
        (f"{SECRET_MEMO} note",))
    docs = folder / "documents"
    docs.mkdir(exist_ok=True)
    (docs / "P03 interview.docx").write_bytes(b"PK\x03\x04 original bytes")
    return folder


def page_of(answer) -> str:
    return Path(answer["location"]).read_text(encoding="utf-8")


class _TextOfMain(HTMLParser):
    """The text a reader sees in <main>, without the code labels, the
    closing names or the note numbers, one line per paragraph."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.skip = 0
        self.depth = 0
        self.lines = []

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if tag == "main":
            self.inside = True
        if not self.inside:
            return
        if self.skip:
            self.skip += 1
        elif {"comment-start", "comment-end", "ref"} & set(classes):
            self.skip = 1
        if tag == "p" and not self.skip:
            self.lines.append("")
            self.depth = 1

    def handle_endtag(self, tag):
        if tag == "main":
            self.inside = False
        if tag == "p":
            self.depth = 0
        if self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if self.inside and self.depth and not self.skip:
            self.lines[-1] += data


def text_of(page: str) -> str:
    parser = _TextOfMain()
    parser.feed(page)
    return "\n".join(parser.lines)


class TestTheReadingCopy:

    def test_written_in_the_reading_folder_and_opened(self, project,
                                                      _no_window_opens):
        answer = host("open_file_for_reading", file_id=50)
        assert answer["shown"] == "reading_copy"
        location = Path(answer["location"])
        assert location.is_file()
        assert location.parent.parent.parent == reading_folder.root()
        assert location.name == "P03 interview.docx - reading copy.html"
        assert _no_window_opens, "the system was not asked to open it"
        assert str(location) in _no_window_opens[-1]
        assert answer["opened"] is False      # the recorder said no
        assert answer["not_opened_because"]

    def test_the_answer_carries_no_text_and_no_memo(self, project):
        text = raw("open_file_for_reading", file_id=50)
        for word in (SECRET_TEXT, SECRET_MEMO, PRIVATE_MEMO, "Opening line",
                     "emoji", "About the file"):
            assert word not in text
        answer = json.loads(text)
        assert set(answer) <= {"file_id", "file_name", "shown", "location",
                               "counts", "opened", "shown_in_folder",
                               "not_opened_because", "note"}

    def test_the_page_holds_the_whole_text_and_the_codings(self, project):
        page = page_of(host("open_file_for_reading", file_id=50))
        assert SECRET_TEXT in page and SECRET_MEMO in page
        assert text_of(page) == TEXT        # whole, spaces and tabs kept
        assert "&lt;script&gt;x&lt;/script&gt;" in page
        assert "<script" not in page.lower()
        assert page.count('class="comment-start"') == 3
        assert page.count('class="comment-end"') == 3

    def test_the_private_part_of_memos_is_left_out(self, project):
        answer = host("open_file_for_reading", file_id=50)
        page = page_of(answer)
        assert PRIVATE_MEMO not in page
        assert "#####" in page          # only in the line that says so
        assert answer["counts"]["private_parts_left_out"] == 2

    def test_a_coding_after_an_emoji_placed_by_qualcoders_count(self,
                                                                 project):
        answer = host("open_file_for_reading", file_id=50)
        assert answer["counts"]["codings_placed_by_second_reading"] == 1
        assert answer["counts"]["codings_matching_neither_reading"] == 0
        page = page_of(answer)
        assert '<span class="k k2 ln0">an emoji</span>' in page


class TestTheOriginal:
    """The original is opened, or shown, only as a read-only copy in the
    reading folder, never as the project's own file."""

    def test_opened_as_a_read_only_copy(self, project, _no_window_opens):
        answer = host("open_file_for_reading", file_id=50, show="original")
        copy = Path(answer["location"])
        own = project / "documents" / "P03 interview.docx"
        assert copy != own and copy.read_bytes() == own.read_bytes()
        assert reading_folder.root() in copy.parents
        assert not os.access(copy, os.W_OK)
        if os.name == "posix":
            assert stat.S_IMODE(copy.stat().st_mode) == 0o400
        assert "not pseudonymised" in answer["note"]
        assert str(copy) in _no_window_opens[-1]
        assert str(own) not in json.dumps(_no_window_opens)

    def test_shown_in_its_folder(self, project, _no_window_opens):
        answer = host("open_file_for_reading", file_id=50, show="in_folder")
        assert answer["shown"] == "in_folder"
        location = Path(answer["location"])
        if sys.platform == "darwin":
            assert _no_window_opens[-1] == ["/usr/bin/open", "-R",
                                            str(location)]
        # On Linux the file manager is asked by the file's address, then
        # (the recorder says no) the folder is opened; elsewhere the path
        # itself is the last argument
        named = {str(location), f"array:string:{location.as_uri()}",
                 str(location.parent)}
        assert any(arg in named for call in _no_window_opens
                   for arg in call)
        assert str(project) not in json.dumps(_no_window_opens)

    def test_asked_twice_the_copy_is_replaced(self, project):
        first = host("open_file_for_reading", file_id=50, show="original")
        second = host("open_file_for_reading", file_id=50, show="original")
        assert first["location"] == second["location"]
        assert "error" not in second

    def test_a_linked_original_is_never_opened(self, project,
                                               _no_window_opens):
        add_file(project, 51, "linked.docx", "Some text.",
                 mediapath="docs:/Users/someone/linked.docx")
        answer = host("open_file_for_reading", file_id=51, show="original")
        assert answer["shown"] == "nothing"
        assert "Manage files" in answer["note"]
        assert _no_window_opens == []

    def test_no_original_gives_the_reading_copy(self, project):
        add_file(project, 52, "typed.txt", "Typed text.", mediapath=None)
        answer = host("open_file_for_reading", file_id=52, show="original")
        assert answer["shown"] == "reading_copy"
        assert "no original" in answer["note"]

    @pytest.mark.parametrize("stored", ["/docs/../data.qda",
                                        "/docs/a:b.docx",
                                        "/docs/sub/x.docx",
                                        "/docs/a\u202eb.docx",
                                        "/docs/tab\tname.docx"])
    def test_a_stored_name_failing_the_rules(self, project, stored,
                                             _no_window_opens):
        name = stored[len("/docs/"):]
        if "/" not in name and ".." not in name:
            try:      # there on the disk, so only the name rules refuse it
                (project / "documents" / name).write_bytes(b"x")
            except OSError:
                pass  # Windows: no such name can exist at all
        add_file(project, 53, "odd.docx", "Text.", mediapath=stored)
        answer = host("open_file_for_reading", file_id=53, show="original")
        assert answer["shown"] == "nothing"
        assert _no_window_opens == []

    def test_a_folder_of_originals_that_is_a_junction(self, project,
                                                      monkeypatch,
                                                      _no_window_opens):
        """Windows' junctions are folders to lstat; the link test sees
        them (here simulated for the documents folder)."""
        real = reading_folder.is_link
        monkeypatch.setattr(reading_folder, "is_link",
                            lambda path: Path(path).name == "documents"
                            or real(path))
        answer = host("open_file_for_reading", file_id=50, show="original")
        assert answer["shown"] == "nothing"
        assert _no_window_opens == []

    def test_an_original_that_is_a_link(self, project, tmp_path,
                                        _no_window_opens):
        secret = tmp_path / "elsewhere.txt"
        secret.write_text("private", encoding="utf-8")
        link = project / "documents" / "link.txt"
        try:
            link.symlink_to(secret)
        except OSError:
            pytest.skip("no symbolic links here")
        add_file(project, 54, "link.txt", "Text.", mediapath="/docs/link.txt")
        answer = host("open_file_for_reading", file_id=54, show="original")
        assert answer["shown"] == "nothing"
        assert _no_window_opens == []

    def test_a_folder_of_originals_that_is_a_link(self, setup_server,
                                                  tmp_path,
                                                  _no_window_opens):
        folder = server._current_project_folder()
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "a.txt").write_text("private", encoding="utf-8")
        try:
            (folder / "documents").symlink_to(elsewhere,
                                              target_is_directory=True)
        except OSError:
            pytest.skip("no symbolic links here")
        add_file(folder, 55, "a.txt", "Text.", mediapath="/docs/a.txt")
        answer = host("open_file_for_reading", file_id=55, show="original")
        assert answer["shown"] == "nothing"
        assert _no_window_opens == []

    def test_the_internet_origin_mark_is_kept(self, project):
        from exegete import origin_mark
        own = project / "documents" / "P03 interview.docx"
        mark = b"0083;66f9c2a1;Mail;"
        if not origin_mark.write(own, mark):
            pytest.skip("this system keeps no internet-origin mark")
        answer = host("open_file_for_reading", file_id=50, show="original")
        assert origin_mark.read(answer["location"]) == mark

    def test_an_unmarked_original_is_not_given_a_mark(self, project):
        from exegete import origin_mark
        answer = host("open_file_for_reading", file_id=50, show="original")
        assert origin_mark.read(answer["location"]) is None

    def test_a_bad_show_and_an_unknown_file(self, project):
        assert "error" in host("open_file_for_reading", file_id=50,
                               show="everything")
        assert "error" in host("open_file_for_reading", file_id=9999)


# The page's structure: only these elements and attributes, whatever the
# project holds (the design, Part 7, "safe by structure").
ALLOWED = {
    "html": {"lang"}, "head": set(), "meta": {"charset", "http-equiv",
                                              "content", "name"},
    "title": set(), "style": set(), "body": set(), "a": {"class", "href",
                                                         "id"},
    "header": set(), "h1": set(), "h2": set(), "h3": set(), "p": {"class"},
    "ul": {"class"}, "ol": set(), "li": {"id"}, "nav": {"class",
                                                        "aria-label"},
    "fieldset": set(), "legend": set(), "input": {"type", "name", "id",
                                                  "checked"},
    "label": {"for"}, "table": set(), "caption": set(), "thead": set(),
    "tbody": set(), "tr": set(), "th": set(), "td": set(),
    "span": {"class", "id", "data-author", "data-code"}, "bdi": set(),
    "sup": {"class", "data-code"}, "main": {"id"}, "section": {"id"},
    "footer": set(),
}


class _Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems = []
        self.metas = []
        self.styles = []
        self.in_style = False
        self.first_tags = []

    def handle_starttag(self, tag, attrs):
        self.first_tags.append(tag)
        allowed = ALLOWED.get(tag)
        if allowed is None:
            self.problems.append(f"element {tag}")
            return
        for name, value in attrs:
            if name not in allowed:
                self.problems.append(f"{tag} attribute {name}")
            if name == "href" and not (value or "").startswith("#"):
                self.problems.append(f"address {value}")
        if tag == "meta":
            self.metas.append(dict(attrs))
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


def structure(page: str) -> _Structure:
    parser = _Structure()
    parser.feed(page)
    return parser


HOSTILE_NAMES = ['</style><script>alert(1)</script>',
                 '"><img src=x onerror=alert(1)>',
                 "x' onmouseover='alert(1)",
                 "a{}body{display:none}", "</bdi></span><a href=//evil>"]


def hostile_page(colour="#FF0000", names=HOSTILE_NAMES):
    from datetime import datetime
    from exegete import reading_copy
    text = "Visit https://example.org now. " * 3 + "\n<b>bold</b>"
    segments = [{"segment_id": i, "position_start": 2 * i,
                 "position_end": 2 * i + 10, "text": None,
                 "memo": f"memo {name}",
                 "code": {"id": 100 + i, "name": name, "color": colour,
                          "category": name}}
                for i, name in enumerate(names)]
    return reading_copy.build_page(
        project_name=names[0], file_id=1, file_name=names[1], text=text,
        segments=segments,
        annotations=[{"position_start": 0, "position_end": 4,
                      "memo": names[2]}],
        file_memo=names[3], written_at=datetime(2026, 10, 1),
        version="test")[0]


class TestThePageIsSafeByStructure:

    def test_only_allowed_elements_and_attributes(self, project):
        for page in (page_of(host("open_file_for_reading", file_id=50)),
                     hostile_page()):
            parsed = structure(page)
            assert parsed.problems == []

    def test_the_head_starts_with_the_character_set_and_the_policy(self):
        page = hostile_page()
        head = page[:page.index("<title>")]
        assert head.index('<meta charset="utf-8">') < head.index(
            "Content-Security-Policy")
        parsed = structure(page)
        assert parsed.metas == [
            {"charset": "utf-8"},
            {"http-equiv": "Content-Security-Policy",
             "content": "default-src 'none'; style-src 'unsafe-inline'; "
                        "form-action 'none'; base-uri 'none'"},
            {"name": "referrer", "content": "no-referrer"}]

    def test_no_project_data_in_the_style_sheet(self):
        style = "".join(structure(hostile_page()).styles)
        for name in HOSTILE_NAMES:
            assert name not in style
        assert "alert" not in style and "evil" not in style

    @pytest.mark.parametrize("colour", ["#FF0000;display:none",
                                        "red", "#FF0000}body{display:none",
                                        "url(https://example.org/x)", None])
    def test_a_colour_carrying_more_is_replaced(self, colour):
        style = "".join(structure(hostile_page(colour=colour)).styles)
        assert "example.org" not in style
        assert "#D8D8D8" in style
        if colour:
            assert colour not in style

    def test_addresses_in_the_text_stay_text(self):
        page = hostile_page()
        assert "https://example.org" in page
        assert 'href="https' not in page
        assert "<img" not in page and "<a href=//" not in page

    def test_selectors_use_numbers(self):
        style = "".join(structure(hostile_page()).styles)
        import re
        for selector in re.findall(r"\.k([^{ ]+)\{", style):
            assert selector.isdigit()


class TestWhatTheAssistantIsTold:

    def _description(self):
        server._apply_toolset("lifecycle")
        return server.mcp.original_descriptions["open_file_for_reading"]

    def test_the_rules_come_first_and_within_the_cut(self):
        text = self._description()
        rules = ("its text does not pass through the conversation",
                 "Call this only when the researcher asks",
                 "never the text",
                 "do not open it, read it or look at it",
                 "is not pseudonymised",
                 "Takes a file id, never a path")
        flat = " ".join(text.split())
        for rule in rules:
            assert rule in flat
            assert flat.index(rule) + len(rule) < 2048
        assert flat.index("Call this only when") < 200
        if sys.version_info[:2] == (3, 13):
            assert len(text) == 997

    def test_in_every_tool_set(self):
        for mode in ("full", "core", "lifecycle"):
            removed = server._apply_toolset(mode)
            try:
                assert "open_file_for_reading" in server.mcp._tool_manager._tools
            finally:
                for name, tool in removed.items():
                    server.mcp._tool_manager._tools[name] = tool

    def test_the_brief_says_so(self):
        brief = " ".join(server.BRIEF_FULL.split())
        assert ("use open_file_for_reading: it opens on their screen and "
                "its text stays off the conversation") in brief
        assert "never open, read or look at them with any tool" in brief

    def test_import_text_file_says_its_text_goes_to_the_provider(self):
        server._apply_toolset("lifecycle")
        text = " ".join(server.mcp.original_descriptions[
            "import_text_file"].split())
        assert text.startswith("Import text typed or pasted in the "
                               "conversation as a new text file. The text "
                               "passes through the conversation, so it "
                               "reaches the AI provider. For a document on "
                               "the researcher's computer use "
                               "import_documents, which keeps its text off "
                               "the conversation. At most 1,000,000 "
                               "characters.")

    def test_skipping_the_backup_on_import_is_deprecated(self, project):
        answer = host("import_text_file", filename="x.txt",
                      content="Some text.", create_backup=False)
        assert "create_backup=false" in json.dumps(answer)
        plain = host("import_text_file", filename="y.txt",
                     content="Some text.")
        assert "create_backup=false" not in json.dumps(plain)


class TestPandocMakesComments:
    """The page, converted file to file with pandoc, gives a Word file
    with one comment per coding, named after its code, and fetches
    nothing. Run where pandoc is installed (the owner's Mac); skipped
    elsewhere."""

    def test_one_comment_per_coding(self, project, tmp_path):
        import shutil
        import subprocess
        import zipfile
        pandoc = shutil.which("pandoc")
        if pandoc is None:
            pytest.skip("pandoc is not installed here")
        version = subprocess.run([pandoc, "--version"], capture_output=True,
                                 text=True, timeout=30).stdout.split()
        if len(version) < 2 or int(version[1].split(".")[0]) < 3:
            pytest.skip("the design checked pandoc 3; this one is older")
        page = host("open_file_for_reading", file_id=50)["location"]
        out = tmp_path / "copy.docx"
        subprocess.run([pandoc, "--sandbox", "-f", "html", "-t", "docx",
                        "-o", str(out), page], check=True, timeout=60,
                       capture_output=True)
        with zipfile.ZipFile(out) as docx:
            comments = docx.read("word/comments.xml").decode("utf-8")
            body = docx.read("word/document.xml").decode("utf-8")
        assert comments.count("<w:comment ") == 3
        assert 'w:author="Stress"' in comments
        assert body.count("<w:commentRangeStart") == 3
        assert SECRET_TEXT in body


class TestOverlapsAndTheStart:

    def test_overlapping_codings_are_both_drawn(self, project):
        page = page_of(host("open_file_for_reading", file_id=50))
        # the second coding starts inside the first: both underlines
        assert '<span class="k k1 ln0 imp"><span class="k k2 ln1">' in page

    def test_the_server_sweeps_the_reading_folder_at_start(self):
        import inspect
        source = inspect.getsource(server.main)
        assert source.index("reading_folder.sweep()") > source.index(
            "_settle_state_folder()")
        assert source.index("reading_folder.sweep()") < source.index(
            'mcp.run(transport="stdio")')
