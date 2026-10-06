# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.2, QualCoder 4.0's release: the owner's ruling of 6 October 2026.

QualCoder 4.0 came out on 2 October 2026 (tag 4.0 at b95e021) and keeps
the project format Exegete was built against. The owner chose:

- to name QualCoder 4.0, the release, as what Exegete is verified
  against, in everything a researcher reads (the README's comparison
  table, TOOLS.md, INSTALL.md, PRIVACY.md, the refusal and warning for a
  project newer than v17, the bug report form), keeping the August
  development commit 9bddf17 only in the code's citations;
- to add two facts, plainly, to the paragraph on QualCoder's own MCP
  server: it calls itself "qualcoder-mcp", Exegete's former name, beside
  an extension named "qualcoder" (so INSTALL.md's advice to keep an
  earlier "qualcoder" entry gains a word of care), and QualCoder's AI
  permission setting governs QualCoder's own assistant and that server,
  not Exegete;
- to leave the tool descriptions' "released QualCoder (3.x)" for
  v0.15 (their words are pinned in `test_v0142_description_cut.py`).

Also pinned: CLAUDE.md's wording after its check (the suite's time,
git's notice, the 2,048 rule's list of exceptions, what protects the
state folder, its map).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from exegete import database, new_project          # noqa: E402


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _flat(name):
    return " ".join(_read(name).replace("\n>", " ").split())


def _between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


# ---------------------------------------------------------------------------
# What Exegete is verified against: the release, by name
# ---------------------------------------------------------------------------

# How the documents named the verified QualCoder before the ruling
COMMIT_AS_VERIFIED = ("verified against QualCoder master",
                      "QualCoder master commit",
                      "valid as of commit",
                      "when 4.0 was in beta",
                      "additionally verified against the QualCoder 4.0-Beta")
READ_BY_RESEARCHERS = ("README.md", "TOOLS.md", "INSTALL.md", "PRIVACY.md",
                       "SUPPORT.md", "AI_CODING_GUIDE.md",
                       "AI_CODING_WORKFLOW.md", "QUICKSTART.md")


def test_the_documents_name_the_release_as_verified():
    for name in READ_BY_RESEARCHERS:
        text = _flat(name)
        for words in COMMIT_AS_VERIFIED:
            assert words not in text, (name, words)
    tools = _flat("TOOLS.md")
    assert ("Exegete is ground-truthed against QualCoder 3.8.2, the latest "
            "stable release until 2 October 2026 (project schema v14), and "
            "verified against QualCoder 4.0, released on 2 October 2026 "
            "(tag `4.0` at `b95e021`, version string \"QualCoder 4.0\"), "
            "whose projects use schema v17.") in tools
    assert ("Parity claims were verified against QualCoder 4.0, and cite "
            "its code at commit `9bddf17` (see \"Supported QualCoder "
            "versions\").") in tools
    install = _flat("INSTALL.md")
    assert ("newer than the schemas this release is verified against (v14 "
            "through v17, up to QualCoder 4.0) are refused to protect the "
            "data") in install
    privacy = _flat("PRIVACY.md")
    assert ("The QualCoder 4.0 behaviour described in this section and the "
            "next two was verified against QualCoder 4.0, released on 2 "
            "October 2026;") in privacy


def test_tools_says_what_the_full_re_check_found():
    versions = _between(_flat("TOOLS.md"), "## Supported QualCoder versions",
                        "A project from a QualCoder older than 3.8")
    for words in (
            "A full re-check against the release (6 October 2026) found "
            "the same project schema (v17) and the same format for a new "
            "project (the format tests now compare every project Exegete "
            "creates with one made by 4.0's own New Project)",
            "the same backups, private memo sections, coder visibility, "
            "\"AI Agent\" coder name, reports, merges and deletes, and the "
            "same fix for the 3.8.2 edit-mode caution (below)",
            "4.0 opened Exegete's new and edited projects with no message, "
            "upgrade or repair",
            "it says \"The project database could not be opened.\" and "
            "changes nothing, and trying again works",
            # what was not re-read, said rather than left out
            "Not yet re-read: the line citations into QualCoder's own MCP "
            "server",
            # and why the documents still cite 9bddf17
            "the line numbers this document and Exegete's code cite from "
            "QualCoder are still those of that commit"):
        assert words in versions, words


def test_the_readme_table_is_checked_against_the_release():
    readme = _flat("README.md")
    assert ("Checked on 6 October 2026, Exegete 0.14.2 against QualCoder "
            "3.8.2 and 4.0:") in readme
    assert ("3.8.2: an AI search finds passages, which you code; 4.0: its "
            "assistant codes as it works, within the AI permission you set "
            "(read only stops it), with undo") in readme
    # the README no longer names the beta or the August commit at all
    for words in ("4.0-Beta", "4.0 beta", "9bddf17"):
        assert words not in readme, words


def test_the_served_refusal_names_the_release():
    assert database.VERIFIED_QUALCODER == "QualCoder 4.0"
    assert new_project.FORMAT_COMMIT == database.VERIFIED_QUALCODER_COMMIT \
        == "b95e021"
    source = (REPO / "src" / "exegete" / "database.py").read_text("utf-8")
    write_support = _between(source, "    def write_support(self):",
                             "    def schema_write_warning(self):")
    assert "VERIFIED_QUALCODER}" in write_support
    assert "master commit" not in write_support


def test_the_code_no_longer_calls_4_0_unreleased_or_a_beta():
    source = (REPO / "src" / "exegete" / "database.py").read_text("utf-8")
    header = source[:source.index("SUPPORTED_DB_VERSIONS")]
    assert "unreleased QualCoder master" not in header
    assert ("v17 (QualCoder 4.0, released 2 October 2026, tag 4.0 at "
            "b95e021)") in " ".join(header.replace("#", " ").split())
    doc = " ".join(new_project.__doc__.split())
    assert "while 4.0 is in beta" not in doc
    assert ("At each of this server's releases, New Project and the upgrade "
            "ladder of QualCoder's newest release are compared with "
            "4.0's;") in doc
    contributing = _flat("CONTRIBUTING.md")
    assert "VERIFIED_MASTER_COMMIT" not in contributing
    assert ("What researchers are told Exegete is verified against is the "
            "release itself, QualCoder 4.0 (`VERIFIED_QUALCODER` in "
            "`database.py`).") in contributing


def test_the_bug_report_form_names_the_release():
    form = _read(".github/ISSUE_TEMPLATE/bug_report.yml")
    for words in ("4.0-Beta", "4.0 Beta", "9bddf17", "a released QualCoder"):
        assert words not in form, words
    assert "description: A release (3.8.x or 4.0)." in form
    assert ("Writes are refused while QualCoder 3.x has the project open, "
            "which its lock file shows; QualCoder 4.0 writes no lock file")\
        in form


def test_the_verified_check_would_notice():
    # The sentences as they stood before the ruling
    for old in ("verified against QualCoder master at commit 9bddf17 "
                "(pulled 2026-08-25, when 4.0 was in beta)",
                "is verified against (v14 through v17, QualCoder master "
                "commit `9bddf17`) are refused",
                "Claims about 4.0 compatibility are valid as of commit "
                "`9bddf17` (2026-08-25).",
                "and additionally verified against the QualCoder 4.0-Beta "
                "pre-release"):
        assert any(words in old for words in COMMIT_AS_VERIFIED), old


# ---------------------------------------------------------------------------
# QualCoder's own MCP server: two more facts, plainly
# ---------------------------------------------------------------------------

def test_the_readme_gives_both_new_facts():
    readme = _flat("README.md")
    facts = _between(readme, "**QualCoder's own MCP server** (checked 6 "
                     "October 2026).", "gives the commits these facts were "
                     "read at.")
    assert ("The server calls itself \"qualcoder-mcp\", Exegete's former "
            "name, and the extension QualCoder's source can build is named "
            "\"qualcoder\", a name an earlier Exegete setup may also use "
            "([INSTALL.md](https://github.com/nicotem/exegete/blob/main/"
            "INSTALL.md#coming-from-qualcoder-mcp) says how to keep the two "
            "apart).") in facts
    assert ("QualCoder's AI permission setting (Read-only, for example) "
            "governs its own assistant and that server, not Exegete.") \
        in facts
    # the facts come before the stance, which keeps its decided words
    assert readme.index("not Exegete.") < readme.index(
        "This project welcomes QualCoder's own server")


def test_tools_gives_both_new_facts():
    tools = _flat("TOOLS.md")
    assert "Four facts about how the tools relate (checked 6 October " \
        "2026)." in tools
    assert ("That server calls itself `qualcoder-mcp`, Exegete's name until "
            "0.14.0, and the Claude Desktop extension QualCoder's source can "
            "build (`tools/mcpb/build_mcpb.py` at the tag) is named "
            "`qualcoder`, a name an earlier Exegete setup may also use for "
            "its own entry:") in tools
    assert ("QualCoder's AI permission setting (Read-only, Sandboxed, the "
            "default, or Full access, stored in `~/.qualcoder/config.ini`, "
            "not in the project) governs QualCoder's own assistant and that "
            "server, not Exegete: Exegete does not read it, so Read-only in "
            "QualCoder does not stop Exegete's writes.") in tools
    assert "Two facts about how the tools relate" not in tools


def test_install_keeps_the_entry_with_a_word_of_care():
    install = _flat("INSTALL.md")
    entry = _between(install, "**Keep your entry.**", "**The settings.**")
    # the advice itself is unchanged
    assert ("keep it, and do not add an `exegete` entry beside it") in entry
    assert ("take care with its name: it calls itself `qualcoder-mcp`, this "
            "server's former name, and the extension QualCoder's source can "
            "build is named `qualcoder`. Added to the same host under the "
            "name `qualcoder`, it could replace this server's entry or be "
            "mistaken for it; a name of its own, such as `qualcoder-app`, "
            "keeps the two apart.") in entry


def test_the_server_names_are_quoted_as_qualcoder_has_them():
    # QualCoder 4.0, tag 4.0: ai_mcp_server.py:102 (server_name) and
    # tools/mcpb/build_mcpb.py:92 ("name"); the setting's labels,
    # GUI/ui_dialog_settings.py:645-647. Exegete's own extension keeps its
    # identity, which these do not share.
    for name in ("README.md", "TOOLS.md", "INSTALL.md"):
        text = _flat(name)
        assert "qualcoder-mcp" in text and "qualcoder" in text, name
    assert "Read-only" in _flat("README.md")
    sys.path.insert(0, str(REPO / "scripts"))
    import build_desktop_extension
    assert build_desktop_extension.EXTENSION_NAME != "qualcoder"


# ---------------------------------------------------------------------------
# CLAUDE.md, after its check
# ---------------------------------------------------------------------------

def test_claude_md_says_what_holds():
    claude = _flat("CLAUDE.md")
    assert ("The full suite takes about twelve minutes on a Mac, longer on "
            "Windows CI;") in claude
    assert "about ten minutes" not in claude
    assert "silently" not in claude
    assert ("git makes up an address from the machine's name, prints a "
            "notice and commits anyway") in claude
    # HOME protects the state folder; the two state variables are read by
    # nothing, so CLAUDE.md does not offer them as protection
    assert ("The server finds that folder through the home folder alone, so "
            "`HOME` (and `USERPROFILE`, for Windows) is what protects it")\
        in claude
    package = [path.read_text(encoding="utf-8")
               for path in (REPO / "src" / "exegete").rglob("*.py")]
    for name in ("EXEGETE_STATE_HOME", "QUALCODER_MCP_STATE_HOME"):
        assert name not in claude, name
        assert not any(name in text for text in package), name
    # the 2,048 rule names where its exceptions are, and they are there
    assert ("listed in `LEFT_PAST_THE_CUT` in "
            "`tests/test_v0142_description_cut.py`") in claude
    assert "LEFT_PAST_THE_CUT = {" in _read(
        "tests/test_v0142_description_cut.py")
    assert ("CONTRIBUTING.md (\"Project structure\") has the full map of "
            "`src/exegete`") in claude
    assert "### Project structure" in _read("CONTRIBUTING.md")
