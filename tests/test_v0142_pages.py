# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, the update site: deployed from GitHub Actions, never from a
branch.

The check for new versions fetches latest.json from the project's
GitHub Pages site, and its notes link to the update page there. The
owner decided on 5 October 2026 that the site is deployed by Actions
(docs/update-check/design.md, D3): a branch would let any token that
can push rewrite latest.json without a release. The port of pull
request #11 prepared the site to be pushed to a `gh-pages` branch, and
CONTRIBUTING.md said it lived there (the port's QA and truth checks,
round 1, 7 October 2026). The site now lives in pages/, and
.github/workflows/pages.yml publishes it.

Pinned here: the site is this release's (scripts/check_pages_site.py,
the check the workflow runs first), and that check notices each way a
site can be wrong; the workflow starts by hand only, from the release's
tag, checks with a read-only token and installs nothing, and deploys
in the `github-pages` environment without checking anything out; no
document sends the site to a branch; the update page gives the check's
whole rule and a PowerShell form for every Terminal command it gives.
"""

import html
import http.server
import importlib.util
import json
import re
import shutil
import sys
import threading
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import release, updates  # noqa: E402

SITE = REPO / "pages"
WORKFLOW = REPO / ".github" / "workflows" / "pages.yml"
RELEASE_DAY = date.fromisoformat(release.RELEASED)


def _script():
    spec = importlib.util.spec_from_file_location(
        "check_pages_site", REPO / "scripts" / "check_pages_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _script()


# ---------------------------------------------------------------------------
# The site is this release's
# ---------------------------------------------------------------------------

def test_the_site_is_this_releases():
    assert check.check_site(SITE, RELEASE_DAY) == []


def test_the_version_file_names_this_release_as_pypi_spells_it():
    data = json.loads((SITE / "latest.json").read_text(encoding="utf-8"))
    assert list(data) == ["format", "version", "released", "important"]
    assert data["format"] == 1 and data["important"] is False
    assert updates.parse_published(data["version"]).display() == \
        release.VERSION
    assert data["released"] == release.RELEASED


@pytest.fixture
def copy(tmp_path):
    site = tmp_path / "pages"
    shutil.copytree(SITE, site)
    return site


def _edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


@pytest.mark.parametrize("name, old, new, problem", [
    ("latest.json", f'"{check.this_release().pep440()}"', '"0.14.1a0"',
     "latest.json names 0.14.1a0"),
    ("latest.json", f'"{release.RELEASED}"', '"2026-10-01"',
     "latest.json is dated 2026-10-01"),
    ("latest.json", '"important": false', '"important": "no"',
     "refused by Exegete"),
    # the page's own date, which a slipped release day would leave behind
    ("update/index.html", updates.spoken_date(RELEASE_DAY),
     "1 October 2026", "does not give the version"),
    # a word of this release's summary (0.14.2's named QualCoder 4.0)
    ("update/index.html", "Word, PDF and other", "Word and other",
     "does not give the summary"),
    ("update/index.html", "/releases/download/v", "/releases/tag/v",
     "does not link the download link"),
    ("update/index.html", "</footer>", "<script>count()</script></footer>",
     "loads or runs something"),
    ("index.html", "</main>",
     '<img alt="" src="https://example.org/pixel.gif"></main>',
     "loads or runs something"),
    ("index.html", "https://github.com/nicotem/exegete\"",
     "https://github.com/nicotem/exegete-mirror\"",
     "links to https://github.com/nicotem/exegete-mirror"),
])
def test_the_check_notices_a_wrong_site(copy, name, old, new, problem):
    _edit(copy / name, old, new)
    problems = check.check_site(copy, RELEASE_DAY)
    assert any(problem in p for p in problems), problems


def test_the_check_notices_a_file_of_another_kind(copy):
    # A branch site needed .nojekyll; an Actions deploy publishes only
    # what is here, and the check holds the list
    (copy / ".nojekyll").write_text("", encoding="utf-8")
    assert any("the site holds" in p for p in check.check_site(
        copy, RELEASE_DAY))


def test_only_this_releases_tag_publishes_it():
    assert check.check_tag(f"v{release.VERSION}") == []
    for ref in ("main", "v0.14.1-alpha", f"{release.VERSION}",
                f"v{release.VERSION}.dev1"):
        assert check.check_tag(ref), ref


# ---------------------------------------------------------------------------
# The live file: never replaced by an earlier release's
# ---------------------------------------------------------------------------

class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = self.server.body
        self.send_response(404 if body is None else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body or b"")))
        self.end_headers()
        self.wfile.write(body or b"")


@pytest.fixture
def live(monkeypatch):
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.daemon_threads = True
    httpd.body = None
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(
        updates, "VERSION_FILE_URL",
        f"http://127.0.0.1:{httpd.server_address[1]}/exegete/latest.json")
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def _version_file(version, released="2026-10-01"):
    return json.dumps({"format": 1, "version": version,
                       "released": released,
                       "important": False}).encode("utf-8")


def test_the_first_publication_has_no_live_file(live):
    assert check.check_live(RELEASE_DAY) == []


def test_the_same_or_an_earlier_release_live_may_be_replaced(live):
    for version in ("0.14.1a0", check.this_release().pep440()):
        live.body = _version_file(version)
        assert check.check_live(RELEASE_DAY) == [], version


def test_a_newer_release_live_is_never_replaced(live):
    live.body = _version_file("9.0.0")
    problems = check.check_live(RELEASE_DAY)
    assert problems and "newer than this release" in problems[0]


def test_a_live_file_that_cannot_be_read_stops_the_publication(live):
    live.body = b"<html>not the file</html>"
    assert check.check_live(RELEASE_DAY)


# ---------------------------------------------------------------------------
# The workflow
# ---------------------------------------------------------------------------

def _workflow():
    return WORKFLOW.read_text(encoding="utf-8")


def _job(name):
    text = _workflow()
    start = text.index(f"\n  {name}:\n")
    following = re.search(r"\n  [A-Za-z0-9_-]+:\n", text[start + 1:])
    return text[start:start + 1 + following.start()] if following \
        else text[start:]


def test_the_workflow_starts_by_hand_only():
    text = _workflow()
    triggers = text[text.index("\non:\n"):text.index("\nconcurrency:")]
    assert triggers.split() == ["on:", "workflow_dispatch:"]


def test_it_publishes_only_from_the_releases_tag():
    check_job = _job("check-site")
    assert "if: github.ref_type != 'tag'" in check_job
    assert ('scripts/check_pages_site.py --tag "$GITHUB_REF_NAME" --live'
            in check_job)
    # and only once the release, its extension file and PyPI's two
    # packages are there, so no notice points to a file not yet there
    assert 'gh release view "$GITHUB_REF_NAME"' in check_job
    assert '"exegete-${display}.mcpb"' in check_job
    assert "for project in exegete qualcoder-mcp" in check_job


def test_the_check_reads_only_and_installs_nothing():
    check_job = _job("check-site")
    permissions = check_job[check_job.index("permissions:"):
                            check_job.index("outputs:")]
    assert permissions.split() == ["permissions:", "contents:", "read"]
    assert "pip install" not in check_job
    assert "persist-credentials: false" in check_job
    assert "actions/upload-pages-artifact@" in check_job
    assert "path: pages" in check_job


def test_the_deploy_waits_for_the_github_pages_environment():
    deploy = _job("deploy-site")
    assert "needs: check-site" in deploy
    permissions = deploy[deploy.index("permissions:"):
                         deploy.index("environment:")]
    assert permissions.split() == ["permissions:", "pages:", "write",
                                   "id-token:", "write"]
    assert "name: github-pages" in deploy
    assert "actions/deploy-pages@" in deploy
    # nothing of the repository runs where the write token is
    assert "actions/checkout@" not in deploy
    assert "python" not in deploy


def test_the_deploy_reads_the_live_file_back_from_exegetes_address():
    # The address as updates.py fixes it (the suite's guard points the
    # module's own at this computer while tests run)
    source = (REPO / "src" / "exegete" / "updates.py").read_text(
        encoding="utf-8")
    address = re.search(r'^VERSION_FILE_URL = "([^"]+)"$', source,
                        re.M).group(1)
    assert address == "https://nicotem.github.io/exegete/latest.json"
    deploy = _job("deploy-site")
    assert f"url={address}" in deploy
    assert "EXPECTED: ${{ needs.check-site.outputs.latest }}" in deploy
    assert '[ "$(cat live.json)" = "$EXPECTED" ]' in deploy


def test_no_document_sends_the_site_to_a_branch():
    places = [REPO / name for name in (
        "README.md", "CONTRIBUTING.md", "INSTALL.md", "PRIVACY.md",
        "CHANGELOG.md", "TOOLS.md", "QUICKSTART.md", "CLAUDE.md")]
    places += sorted((REPO / "docs" / "update-check").glob("*.md"))
    places += sorted((REPO / ".github" / "workflows").glob("*.y*ml"))
    places += sorted((REPO / "scripts").glob("*.py"))
    for path in places:
        assert "gh-pages" not in path.read_text(encoding="utf-8"), path
    contributing = " ".join(
        (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8").split())
    assert ("The site is published by `.github/workflows/pages.yml`, "
            "deployed from GitHub Actions and never from a branch"
            ) in contributing


# ---------------------------------------------------------------------------
# The update page's words
# ---------------------------------------------------------------------------

def _page():
    return (SITE / "update" / "index.html").read_text(encoding="utf-8")


def _words(text):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", text)).split())


def test_the_page_gives_the_checks_whole_rule():
    # The port's privacy check, round 1: "at most once a week" left out
    # the check made when the researcher asks
    assert ("Exegete checks whether a newer version exists at most once a "
            "week, and when you ask,") in _words(_page())


def _blocks():
    return [html.unescape(block) for block in
            re.findall(r"<pre><code>(.*?)</code></pre>", _page(), re.S)]


_POSIX_PYTHON = re.compile(r'^"(\$HOME/[^"]*)/bin/python" (.*)$')


def test_every_terminal_command_has_its_powershell_form():
    """The port's truth check, round 1: the page said "PowerShell on
    Windows" but gave the copy of the source and the earlier name a Mac
    form only, which PowerShell cannot run (no `&`, `bin/python`). Each
    command with an environment's Python is checked against the form the
    code itself gives (updates._command)."""
    blocks = _blocks()
    checked = 0
    for block in blocks:
        if "/bin/python" not in block:
            continue
        windows = []
        for line in block.splitlines():
            match = _POSIX_PYTHON.match(line)
            if match:
                folder, rest = match.groups()
                assert line == updates._command(
                    False, f"{folder}/bin/python", rest)
                line = updates._command(
                    True, folder.replace("/", "\\")
                    + "\\Scripts\\python.exe", rest)
            elif line.startswith('cd "$HOME/'):
                line = line.replace("/", "\\")
            windows.append(line)
        assert "\n".join(windows) in blocks, "\n".join(windows)
        checked += 1
    assert checked == 3


# ---------------------------------------------------------------------------
# The records say what is still open
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("record", ["design.md", "wording.md"])
def test_the_records_say_the_real_computer_checks_are_open(record):
    """The port's privacy check, round 1: the design's own condition
    (items 1 to 6 of its section 13 on a real Mac and a real Windows
    computer before a release carries the check) was unmet, and the
    records' note on the port did not say so."""
    text = (REPO / "docs" / "update-check" / record).read_text(
        encoding="utf-8")
    note = text[text.index("**Since the port onto 0.14.2"):]
    note = " ".join(note[:note.index("\n\n")].split())
    assert "none of the checks on a real computer in" in note
    assert ("items 1 to 6 must pass on a real Mac and a real Windows "
            "computer before a release carries the check") in note
    # v0.14.2's last round: the owner's choice of 7 October (ruling 61)
    # includes item 6, which the checklist for his sitting had left out
    assert ("On 7 October 2026 the owner chose to make items 1 to 4 and 6 "
            "on his Mac, in his check of the brief with the final test "
            "build of this branch") in note
    assert ("the Install button's label when Exegete is already installed, "
            "and whether the settings chosen before (the tool set and the "
            "folder for projects) survive the update") in note
    assert "Windows has not been checked by hand yet" in note
    assert "Whether 0.14.2 waits for them" not in note
    # and the site's change is in the same note, with D3 kept
    assert "never from a branch, as D3 decided" in note


def test_item_6_says_how_to_check_it():
    """v0.14.2's last round: section 13's item 6 says what to note while
    installing one build over another, since the owner's sitting takes
    it from there (ruling 61)."""
    text = " ".join((REPO / "docs" / "update-check" / "design.md")
                    .read_text(encoding="utf-8").split())
    section = text[text.index("## 13. To verify on a real computer"):]
    item = section[section.index(" 6. The install button's label"):
                   section.index(" 7. Windows app-package")]
    assert ("To check it: before installing a test build over an earlier "
            "one, note the tool set and the folder for projects in "
            "Settings, Extensions, Exegete; while installing, note the "
            "label of the button the installation screen shows; afterwards, "
            "before changing anything, look at the same two settings "
            "again.") in item
