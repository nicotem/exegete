# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.3 (ruling 117, item 3): a security fault is reported privately.

GitHub's private vulnerability reporting was switched on for the
repository on 5 November 2026. SECURITY.md says how to use it and asks
for no participants' data; CONTRIBUTING points to it instead of to a
public issue.
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
