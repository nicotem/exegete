# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3 (ruling 117, item 3): a security fault is reported privately.

GitHub's private vulnerability reporting was switched on for the
repository on 5 November 2026. SECURITY.md says how to use it and asks
for no participants' data; CONTRIBUTING points to it instead of to a
public issue. From v0.15.4 the bug report form, the issue configuration
and SUPPORT point to it too.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FORM = "https://github.com/nicotem/exegete/security/advisories/new"


def _flat(name):
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def test_security_md_gives_the_private_form_and_asks_for_no_data():
    security = _flat("SECURITY.md")
    assert FORM in security
    assert "privately" in security
    assert "without copying participants' data" in security


def test_contributing_sends_a_security_concern_to_security_md():
    contributing = _flat("CONTRIBUTING.md")
    assert "[SECURITY.md](SECURITY.md)" in contributing
    assert "Report a security concern the same way. Open an issue" \
        not in contributing


SECURITY_PAGE = "https://github.com/nicotem/exegete/blob/main/SECURITY.md"


def test_the_issue_forms_and_support_send_such_a_fault_to_security_md():
    """v0.15.4: the bug report form, the issue configuration and SUPPORT
    no longer say that everything goes through GitHub Issues. Each points
    to SECURITY.md's private report for a fault that could expose
    participants' data or let a write damage a project, as CONTRIBUTING
    does, before anything is written in public."""
    form = (REPO / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(
        encoding="utf-8")
    opening = form[form.index("value: |"):form.index("- type: textarea")]
    assert f"[SECURITY.md]({SECURITY_PAGE})" in opening
    assert opening.index("best reported privately") < \
        opening.index("An issue is public.")
    config = (REPO / ".github/ISSUE_TEMPLATE/config.yml").read_text(
        encoding="utf-8")
    link = config[config.index(f"url: {SECURITY_PAGE}"):]
    assert link.split("\n")[1].strip().startswith("about: A fault that "
                                                   "could expose")
    assert "best reported privately" in link
    assert "Everything goes through" not in config
    support = _flat("SUPPORT.md")
    assert "Everything goes through" not in support
    opening = support[support.index("## Where to get help"):]
    opening = opening[:opening.index("- **Bug reports.**")]
    assert ("is best reported privately instead, so that it is not public "
            "before its fix. [SECURITY.md](SECURITY.md) says how.") in opening
    assert (REPO / "SECURITY.md").is_file()
