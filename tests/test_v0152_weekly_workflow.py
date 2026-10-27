# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2: the weekly checks (.github/workflows/advisories.yml and
.github/workflows/qualcoder-watch.yml).

- The advisory check (`scripts/check_advisories.py`) also asks about
  the official validator's libraries, from their own lock
  (`packaging/desktop-extension/validator/package-lock.json`, npm), in
  the same request as uv.lock's (PyPI). The four advisories OSV gives
  for the validator today are accepted in a list of their own,
  KNOWN_NPM, read only when that lock is asked, so a run given uv.lock
  alone never says they can go. A lock of another name or form is not
  read: exit 2, with nothing asked.
- The watch on QualCoder's newest code runs once a week in a workflow
  of its own, and no longer in ci.yml, whose parity job compares with
  QualCoder 4.0 alone. The watch runs the parity job's tests, installs
  from the lock, and is red when QualCoder's newest code stores a
  different text; its step summary names the documents and QualCoder's
  commit (`scripts/qualcoder_parity.py --check`).

No test reaches the network: OSV's answer is replaced, and the watch's
comparison is given a fixed result. That GitHub runs the workflows is
shown by their runs on the piece's branch.
"""

import json
import os
import re
import sys
from pathlib import Path

import pytest

from test_v012_workflow_pins import WORKFLOWS, _jobs
from test_v0151_libraries import EXPORT, LOCKED_INSTALL
from test_v0151_library_checks import _Opener, _steps, advisories

REPO = Path(__file__).resolve().parent.parent
VALIDATOR_LOCK = (REPO / "packaging" / "desktop-extension" / "validator" /
                  "package-lock.json")
NPM_REGISTRY = "https://registry.npmjs.org/"


def _npm_entries():
    """The validator's lock read here on its own: (name, version) of each
    entry under node_modules/ resolved from npm's registry."""
    lock = json.loads(VALIDATOR_LOCK.read_text(encoding="utf-8"))
    return [(path.rsplit("node_modules/", 1)[1], entry["version"])
            for path, entry in lock["packages"].items()
            if "node_modules/" in path
            and entry.get("resolved", "").startswith(NPM_REGISTRY)]


def _answer_for(pairs, ids_by_name=None):
    """OSV's querybatch answer for `pairs`, in order: the ids given for a
    library's name, none for the others."""
    ids_by_name = ids_by_name or {}
    return {"results": [
        {"vulns": [{"id": vid, "modified": "2026-10-01"}
                   for vid in ids_by_name[name]]}
        if ids_by_name.get(name) else {} for name, _ in pairs]}


def _known_npm_ids():
    """{library: [ids]} of KNOWN_NPM, as OSV would report them."""
    ids = {}
    for advisory, (library, _, _, _) in advisories.KNOWN_NPM.items():
        ids.setdefault(library, []).append(advisory)
    return ids


@pytest.fixture
def actions(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


# ---------------------------------------------------------------------------
# The validator's lock in the advisory check
# ---------------------------------------------------------------------------

def test_the_validators_lock_is_asked_with_the_libraries(actions):
    """Each registry entry of the validator's lock, a scoped name with its
    scope; then one request for both locks, uv.lock's releases asked in
    PyPI and the validator's in npm."""
    pairs = advisories.locked_releases(VALIDATOR_LOCK)
    assert pairs == _npm_entries()
    package = json.loads((VALIDATOR_LOCK.parent / "package.json").read_text(
        encoding="utf-8"))
    for name, version in package["devDependencies"].items():
        assert (name, version) in pairs, name
    libraries = advisories.locked_releases(REPO / "uv.lock")
    opener = _Opener(_answer_for(libraries + pairs))
    assert advisories.main([str(REPO / "uv.lock"), str(VALIDATOR_LOCK)],
                           opener=opener, sleep=lambda s: None) == 0
    [request] = opener.requests
    queries = json.loads(request.data)["queries"]
    assert [(q["package"]["ecosystem"], q["package"]["name"], q["version"])
            for q in queries] == (
        [("PyPI", name, version) for name, version in libraries]
        + [("npm", name, version) for name, version in pairs])


def test_a_new_validator_advisory_fails_and_a_known_one_is_a_notice(
        actions, tmp_path, monkeypatch, capsys):
    """The four accepted on 27 October against the validator's lock as it
    is: a notice each, exit 0. A fifth id fails, named; the summary's
    rows begin with their registry."""
    pairs = advisories.locked_releases(VALIDATOR_LOCK)
    known = _known_npm_ids()
    assert advisories.main([str(VALIDATOR_LOCK)],
                           opener=_Opener(_answer_for(pairs, known))) == 0
    out = capsys.readouterr().out
    assert out.count("::notice title=Known advisory::") == 4
    assert "::error" not in out

    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    more = dict(known, zod=[*known["zod"], "GHSA-zzzz-zzzz-zzzz"])
    assert advisories.main([str(VALIDATOR_LOCK)],
                           opener=_Opener(_answer_for(pairs, more))) == 1
    errors = [line for line in capsys.readouterr().out.splitlines()
              if line.startswith("::error")]
    zod = dict(pairs)["zod"]
    assert errors == [f"::error title=New advisory::zod {zod}: "
                      f"GHSA-zzzz-zzzz-zzzz"]
    rows = [line for line in summary.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ") and "GHSA-" in line]
    assert len(rows) == 5 and all(row.startswith("| npm | ") for row in rows)
    assert f"| npm | zod | {zod} | GHSA-zzzz-zzzz-zzzz | new |" in rows


def test_known_advisories_are_gone_only_for_the_locks_asked(actions, capsys):
    """An accepted advisory no longer reported is named only when its
    lock was asked: uv.lock alone never names the validator's four; both
    locks with none reported name the four, in KNOWN_NPM."""
    libraries = advisories.locked_releases(REPO / "uv.lock")
    pairs = advisories.locked_releases(VALIDATOR_LOCK)
    assert advisories.main([str(REPO / "uv.lock")],
                           opener=_Opener(_answer_for(libraries))) == 0
    gone = [line for line in capsys.readouterr().out.splitlines()
            if "no longer reported:" in line]
    assert gone and not any(advisory in line for line in gone
                            for advisory in advisories.KNOWN_NPM)

    assert advisories.main([str(REPO / "uv.lock"), str(VALIDATOR_LOCK)],
                           opener=_Opener(_answer_for(libraries + pairs))) == 0
    gone = [line for line in capsys.readouterr().out.splitlines()
            if "no longer reported:" in line]
    for advisory in advisories.KNOWN_NPM:
        [line] = [line for line in gone if advisory in line]
        assert "its entry in KNOWN_NPM can go" in line
    assert not set(advisories.KNOWN) & set(advisories.KNOWN_NPM)


NPM_ENTRY = {"version": "1.0.0",
             "resolved": f"{NPM_REGISTRY}left-pad/-/left-pad-1.0.0.tgz",
             "integrity": "sha512-x", "dev": True}


@pytest.mark.parametrize("name, text", [
    # another name, though written as a uv.lock is
    ("yarn.lock", '[[package]]\nname = "anyio"\nversion = "4.15.1"\n'
                  'source = { registry = "https://pypi.org/simple" }\n'),
    # an older form of package-lock.json
    ("package-lock.json", json.dumps({
        "lockfileVersion": 2,
        "packages": {"": {}, "node_modules/left-pad": NPM_ENTRY},
        "dependencies": {"left-pad": {"version": "1.0.0"}}})),
    # no entry from npm's registry: a local folder linked
    ("package-lock.json", json.dumps({
        "lockfileVersion": 3,
        "packages": {"": {}, "node_modules/local": {
            "resolved": "file:../local", "link": True}}})),
    # a registry entry with no release
    ("package-lock.json", json.dumps({
        "lockfileVersion": 3,
        "packages": {"node_modules/left-pad": {
            k: v for k, v in NPM_ENTRY.items() if k != "version"}}})),
    ("package-lock.json", "[]"),
    ("package-lock.json", "not json"),
])
def test_a_lock_of_another_name_or_form_exits_2(tmp_path, capsys, name,
                                                text):
    """Nothing is asked, even beside a lock that can be read."""
    lock = tmp_path / name
    lock.write_text(text, encoding="utf-8")
    opener = _Opener()
    assert advisories.main([str(REPO / "uv.lock"), str(lock)],
                           opener=opener, sleep=lambda s: None) == 2
    assert opener.requests == []
    assert str(lock) in capsys.readouterr().err
