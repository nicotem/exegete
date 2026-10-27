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
    entry under node_modules/ resolved from npm's registry, by the name
    npm writes in the entry when it has one (an alias), else the folder's."""
    lock = json.loads(VALIDATOR_LOCK.read_text(encoding="utf-8"))
    return [(entry.get("name") or path.rsplit("node_modules/", 1)[1],
             entry["version"])
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


def test_an_aliased_library_is_asked_by_its_own_name(tmp_path):
    """npm writes the library's own name in the entry of one installed
    under another name: OSV is asked about that library, not the folder's
    name, which can be another library on npm."""
    lock = tmp_path / "package-lock.json"
    lock.write_text(json.dumps({"lockfileVersion": 3, "packages": {
        "": {},
        "node_modules/string-width-cjs": {
            "name": "string-width", "version": "4.2.3",
            "resolved": f"{NPM_REGISTRY}string-width/-/"
                        f"string-width-4.2.3.tgz"},
        "node_modules/@scope/tool": {
            "version": "1.0.0",
            "resolved": f"{NPM_REGISTRY}@scope/tool/-/tool-1.0.0.tgz"}}}),
        encoding="utf-8")
    assert advisories.locked_releases(lock) == [
        ("string-width", "4.2.3"), ("@scope/tool", "1.0.0")]


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


# ---------------------------------------------------------------------------
# The watch on QualCoder's newest code
# ---------------------------------------------------------------------------

def _parity():
    scripts = str(REPO / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import qualcoder_parity
    return qualcoder_parity


def test_the_watch_writes_its_count_to_the_step_summary(tmp_path,
                                                        monkeypatch):
    """`--check`, with a fixed result in place of QualCoder's functions:
    the step summary holds QualCoder's commit, the count and the names of
    the documents whose outcome changed; exit 1, then 0 with none."""
    parity = _parity()
    files = {"a.txt": {"text": "one"}, "b.pdf": {"text": "two"}}
    monkeypatch.setattr(parity, "run", lambda tree: {
        "qualcoder_source": str(tree), "versions": {}, "files": dict(files)})
    recorded = tmp_path / "expected.json"
    recorded.write_text(json.dumps(
        {"files": dict(files, **{"b.pdf": {"text": "2"}})}), encoding="utf-8")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    args = ["--qualcoder", str(tmp_path), "--commit", "abc1234",
            "--check", str(recorded)]
    assert parity.main(args) == 1
    lines = summary.read_text(encoding="utf-8").splitlines()
    assert any("abc1234" in line for line in lines)
    assert "1 of 2 outcomes changed since the recorded run" in lines
    assert "- b.pdf" in lines and not any("a.txt" in line for line in lines)

    recorded.write_text(json.dumps({"files": files}), encoding="utf-8")
    assert parity.main(args) == 0
    assert "0 of 2 outcomes changed since the recorded run" in \
        summary.read_text(encoding="utf-8").splitlines()


WATCH = WORKFLOWS / "qualcoder-watch.yml"
WATCH_JOB = "qualcoder-watch"
TESTS_STEP = "Exegete's text against QualCoder's"
PARITY_STEP = "What QualCoder's newest code stores differently"


def _rows(job):
    """A job's lines, stripped, comments left out."""
    return [line.strip() for line in job["lines"]
            if not line.lstrip().startswith("#")]


def _parity_job():
    return next(job for job in _jobs(WORKFLOWS / "ci.yml")
                if job["name"] == "qualcoder-parity")


def test_the_watch_runs_weekly_in_its_own_workflow():
    """Mondays, by hand, and on a push that changes the workflow alone;
    QualCoder at its newest code, read only; red when its tests fail and
    nowhere else; the comparison run once the tests have run."""
    text = WATCH.read_text(encoding="utf-8")
    assert '- cron: "0 6 * * 1"' in text
    assert "\n  workflow_dispatch:\n" in text
    paths = re.search(r"\n    paths:\n((?:      - .+\n)+)", text).group(1)
    assert re.findall(r'"([^"]+)"', paths) == [
        ".github/workflows/qualcoder-watch.yml"]
    [job] = _jobs(WATCH)
    assert job["name"] == WATCH_JOB
    assert "    timeout-minutes: 20" in job["lines"]
    assert not any("continue-on-error" in row for row in _rows(job))
    steps = {name: [row.strip() for row in lines.splitlines()]
             for name, lines in _steps(WATCH.name, WATCH_JOB).items()}
    source = steps["Check out QualCoder's newest code, read only"]
    for row in ("repository: ccbogel/QualCoder", "ref: master",
                "persist-credentials: false"):
        assert row in source, row
    tests = steps[TESTS_STEP]
    for row in ("id: tests", "shell: bash", "set +e",
                "QUALCODER_SOURCE: ${{ github.workspace }}/qualcoder-src",
                'EXEGETE_PARITY_GATE: ""', "code=${PIPESTATUS[0]}",
                '} >> "$GITHUB_STEP_SUMMARY"'):
        assert row in tests, row
    assert tests[-1] == "exit $code"
    assert any(row.endswith('2>&1 | tee "$RUNNER_TEMP/pytest_output.txt"')
               for row in tests)
    parity = steps[PARITY_STEP]
    assert parity[0] == \
        "if: ${{ !cancelled() && steps.tests.outcome != 'skipped' }}"
    assert any("python scripts/qualcoder_parity.py --qualcoder "
               "qualcoder-src --commit \"$commit\" --check "
               "tests/fixtures/import_expected.json" in row for row in parity)
    assert list(steps).index(TESTS_STEP) < list(steps).index(PARITY_STEP)


def test_ci_compares_with_qualcoder_4_0_alone():
    """The parity job in ci.yml, one job at QualCoder 4.0 with the
    release's own checks switched on; the watch no longer runs there."""
    rows = _rows(_parity_job())
    assert "ref: b95e021c93eb29a646ee7a8de196c281b7890ddf" in rows
    assert 'EXEGETE_PARITY_GATE: "1"' in rows
    for gone in ("matrix", "continue-on-error", "master", "--check"):
        assert not any(gone in row for row in rows), gone
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "ref: master" not in ci and "qualcoder_parity.py --" not in ci


def test_the_watch_runs_the_parity_jobs_tests_from_the_lock():
    """The same pytest command as the parity job, read before the watch's
    `2>&1 | tee`, so the newest code is checked by every test the 4.0
    release is; the install from the lock, with the optional part."""
    def command(rows):
        [row] = [row for row in rows if "python -m pytest" in row]
        return row[row.index("python -m pytest"):].split(" 2>&1")[0]

    [job] = _jobs(WATCH)
    watch = _rows(job)
    assert command(watch) == command(_rows(_parity_job()))
    assert EXPORT.format(" --extra pdf-epub") in watch
    for row in LOCKED_INSTALL:
        assert row in watch, row
    text = "\n".join(watch)
    assert 'pip install -e ".[' not in text
    assert text.index("--require-hashes") < text.index("python -m pytest")
