# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.12 Batch A, fix round 1 (F5): the version comments beside the
SHA-pinned GitHub Actions have to stay truthful.

Dependabot rewrites the SHA and, when the trailing comment carries a
suffix such as "(release/v1)", it does not always rewrite the version
next to it. That is how `pypa/gh-action-pypi-publish` came to sit at the
v1.14.2 SHA under a "# v1.14.1" comment while the CHANGELOG repeated the
stale number. Nothing in the suite noticed.

Fix round 2, R5: the round-1 version of this file checked internal
consistency only, and the incident was internally CONSISTENT (both
`uses:` lines carried the stale number and so did the CHANGELOG), so it
would have passed on the pre-fix tree. The three consistency tests are
kept, because they catch a half-rewritten bump cheaply, but the check
that catches the incident itself is the ledger below: every pinned SHA is
recorded against the tag it really dereferences to upstream, so a comment
that disagrees with the SHA fails here however consistent the rest of the
tree is.

The ledger is the offline record of an online check, and a SHA that is
not in it is a failure rather than a pass: bumping a pin therefore means
dereferencing the new tag and recording the pair, which is exactly the
step that was skipped. For owner/action at tag vX.Y.Z:

    curl -s https://api.github.com/repos/<owner>/<action>/git/ref/tags/vX.Y.Z

reading `.object.sha`, and when `.object.type` is "tag" (an annotated
tag, as pypa/gh-action-pypi-publish uses) the commit is one hop further:

    curl -s https://api.github.com/repos/<owner>/<action>/git/tags/<sha>

No test here reaches the network: CI cannot assume it, and a suite that
silently skipped the check offline would be the same hole again.

Fix round 3, S2: the ledger read `*.yml` only. A workflow added as
`*.yaml` is equally valid to GitHub Actions and was scanned by nobody,
while every test here kept passing because the two existing files supply
the ten pins the anti-vacuity guard asks for. The scan is now
`_scanned_files()`, which reads both spellings plus any composite action
under .github/actions, refuses a file in .github/workflows it cannot
read, and is itself pinned against the directory listing.

Fix round 4, T4: the permissions pin S3 added had the same shape. Its
job-key pattern missed two legal YAML spellings, a trailing comment and
a quoted key, and an unmatched line was SKIPPED rather than refused, so
jobs written either way escaped the permissions check while every test
here stayed green. The pattern now covers those spellings, a line that
sits where a job key sits and is not one this ledger can read is a
failure, and the jobs found are checked against a recorded ledger rather
than a floor. Same rule as the SHA ledger: assert what was scanned, and
fail on what could not be.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ACTIONS = REPO_ROOT / ".github" / "actions"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# (action, commit SHA) -> the tag whose tip that commit is, each pair
# dereferenced against the public GitHub API on 2026-09-13 with the two
# commands in the module docstring. The superseded gh-action-pypi-publish
# pin is kept as the F5 incident's ground truth: the old SHA belongs to
# v1.14.1, the current one to v1.14.2, which is what the stale comment
# got wrong.
VERIFIED_TAGS = {
    ("actions/checkout",
     "3d3c42e5aac5ba805825da76410c181273ba90b1"): "v7.0.1",
    ("actions/setup-python",
     "5fda3b95a4ea91299a34e894583c3862153e4b97"): "v7.0.0",
    ("actions/upload-artifact",
     "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"): "v7.0.1",
    ("actions/download-artifact",
     "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"): "v8.0.1",
    ("pypa/gh-action-pypi-publish",
     "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"): "v1.14.2",
    ("pypa/gh-action-pypi-publish",
     "ba38be9e461d3875417946c167d0b5f3d385a247"): "v1.14.1",
    # v0.14.2, the update site published from Actions (pages.yml):
    # dereferenced on 2026-10-07 with the same commands, both lightweight
    # tags (`.object.type` "commit")
    ("actions/upload-pages-artifact",
     "fc324d3547104276b827a68afc52ff2a11cc49c9"): "v5.0.0",
    ("actions/deploy-pages",
     "368f82528645a54fb793d4d04e342629a3f51346"): "v5.0.1",
}

# owner/action@sha  # vX.Y.Z[ (suffix)]
PIN_RE = re.compile(
    r"uses:\s*(?P<action>[\w.-]+/[\w.-]+)@(?P<sha>[0-9a-f]{40})"
    r"\s*#\s*(?P<version>v[\w.]+)(?P<suffix>\s*\([^)]*\))?"
)


def _rel(path):
    """Repo-relative posix label, or the bare name off the repository.

    The parser below is exercised against synthetic workflows under
    tmp_path (fix round 4, T4), which `relative_to` refuses, and on
    Windows tmp_path can even be on another drive.
    """
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _scanned_files():
    """Every file the ledger reads, and a refusal to leave one unread.

    Fix round 3, S2: the glob was `*.yml`, and GitHub Actions treats
    `.yaml` as equally valid, so a workflow added under that spelling was
    scanned by nobody while all four tests here still passed (the
    anti-vacuity guard is satisfied by the two existing files on its
    own). Composite actions under .github/actions are read for the same
    reason; rglob over a directory that does not exist yields nothing, so
    this is safe while the repository has none.

    The `stray` refusal is what stops the next spelling surprise rather
    than only the one known spelling: a workflow committed as .yamlx, or
    with no suffix at all, fails here instead of escaping the ledger.
    Names beginning with a dot are not workflows and are skipped, so a
    Finder-planted .DS_Store does not fail the suite.
    """
    stray = sorted(path.name for path in WORKFLOWS.iterdir()
                   if path.is_file() and not path.name.startswith(".")
                   and path.suffix not in {".yml", ".yaml"})
    assert not stray, (
        f"files in .github/workflows that this ledger cannot scan: {stray}. "
        f"GitHub Actions reads .yml and .yaml; anything else here is either "
        f"a mistake or a change this test has to learn about.")
    return sorted([*WORKFLOWS.glob("*.y*ml"), *ACTIONS.rglob("action.y*ml")])


def test_the_ledger_scans_every_workflow_file_on_disk():
    """Non-vacuity for the scan itself, not only for the pins it found.

    A glob that matches nothing, or matches less than the directory
    holds, makes every other test in this file pass by default.
    """
    scanned = _scanned_files()
    assert scanned, f"nothing scanned under {WORKFLOWS}"
    on_disk = sorted(path for path in WORKFLOWS.iterdir()
                     if path.is_file() and not path.name.startswith("."))
    assert [path.name for path in scanned if path.parent == WORKFLOWS] == \
        [path.name for path in on_disk]
    # And the two that carry the pins are among them, so a rename cannot
    # empty the scan quietly.
    assert {"ci.yml", "publish.yml"} <= {path.name for path in scanned}


def _pins():
    found = []
    for path in _scanned_files():
        rel = _rel(path)
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "uses:" not in line:
                continue
            match = PIN_RE.search(line)
            # The path is relative to the repository root, not the bare
            # file name: two composite actions are both `action.yml`
            # (fix round 3, S2).
            assert match is not None, f"{rel}:{line_no} {line.strip()}"
            found.append({
                "where": f"{rel}:{line_no}",
                "action": match.group("action"),
                "sha": match.group("sha"),
                "version": match.group("version"),
                "suffix": (match.group("suffix") or "").strip(),
            })
    return found


# A workflow's jobs and steps, read as text. PyYAML is not a declared dev
# dependency (pyproject's [dev] set is pytest, pytest-asyncio, xmlschema,
# hypothesis, build and twine), so a test that imported it would pass in
# the maintainer's venv and error in CI. These two regexes read the two
# indentation levels the workflow files actually use.
TOP_KEY_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+):")
# Fix round 4, T4: the round-3 spelling was r"^  ([A-Za-z0-9_.-]+):\s*$",
# which recognised a job only when the key ended immediately after the
# colon and carried no quotes. `  deploy:   # staging only` and
# `  "deploy":` are both legal YAML and both were SKIPPED rather than
# refused, so a workflow with one compliant job and two non-compliant
# ones passed every test in this file: the anti-vacuity guard asked only
# that each FILE contribute a job, not each job in it. The optional
# backreferenced quote group covers single and double quotes and still
# rejects a mismatched one; the optional trailing comment is the other
# legal spelling. Anything else at this indent is refused in _jobs()
# rather than skipped, which is the half that makes this a ledger.
JOB_KEY_RE = re.compile(
    r"""^  (?P<q>["']?)(?P<name>[A-Za-z0-9_.-]+)(?P=q):\s*(\#.*)?$""")
JOB_PERMISSIONS_RE = re.compile(r"^    permissions:")

# Every job in every workflow, recorded rather than counted (fix round 4,
# T4). `len(jobs) >= 4` and "each file contributes a job" are both
# satisfied while a job goes missing from the scan; an exact ledger is
# not. Adding, renaming or removing a job means recording it here, the
# same step VERIFIED_TAGS asks for when an action pin moves.
WORKFLOW_JOBS = {
    # v0.14: the desktop extension's build and its cross-platform check.
    "ci.yml": {"test", "desktop-extension", "desktop-extension-same",
               # v0.14.1: the rename's old name's package and upgrades.
               "rename-upgrade",
               # 0.14.3: the import's text against QualCoder's own code.
               "qualcoder-parity",
               # v0.15.1: the links in the documents, on every push.
               "documents",
               # v0.15.1: the suite on the newest library releases,
               # reporting only.
               "newest-libraries",
               # v0.15.2: which tier the run takes
               # (tests/test_v0152_ci_tier.py).
               "tier"},
    "publish.yml": {"build", "publish-to-testpypi", "publish-to-pypi"},
    # v0.14.2: the update site, deployed from Actions, never from a branch
    # (the owner's decision of 5 October 2026)
    "pages.yml": {"check-site", "deploy-site"},
    # v0.15.1: the links to other sites, once a week
    "external-links.yml": {"external-links"},
    # v0.15.1: the locked releases against the advisories, once a week
    "advisories.yml": {"advisories"},
    # v0.15.2: the import's text against QualCoder's newest code, once a
    # week (it ran in ci.yml's parity job before)
    "qualcoder-watch.yml": {"qualcoder-watch"},
}


def _jobs(path):
    """[{name, where, lines}] for each job in a workflow file.

    Fix round 4, T4: a line at exactly two spaces of indent inside the
    `jobs:` block that is neither blank nor a comment is a job key this
    parser does not understand, and it is refused here. Skipping it was
    the defect: the job dropped out of the permissions check, and its
    body was absorbed into the PRECEDING job, so the permissions block of
    one job vouched for another.
    """
    jobs = []
    in_jobs = False
    current = None
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if TOP_KEY_RE.match(line):
            in_jobs = line.startswith("jobs:")
            current = None
            continue
        if not in_jobs:
            continue
        two_space_key = (line.startswith("  ")
                         and not line.startswith("   ")
                         and line.strip()
                         and not line.lstrip().startswith("#"))
        match = JOB_KEY_RE.match(line)
        assert match is not None or not two_space_key, (
            f"{_rel(path)}:{line_no} "
            f"{line.strip()!r} sits where a job key sits but is not one "
            f"this ledger can read. Teach JOB_KEY_RE the spelling rather "
            f"than letting the job escape the permissions check.")
        if match:
            current = {
                "name": match.group("name"),
                "where": f"{_rel(path)}:{line_no}",
                "lines": [],
            }
            jobs.append(current)
        elif current is not None:
            current["lines"].append(line)
    return jobs


def _workflow_level_permissions(path):
    """True when the workflow declares permissions above its jobs."""
    return any(TOP_KEY_RE.match(line) and line.startswith("permissions:")
               for line in path.read_text(encoding="utf-8").splitlines())


def _jobs_without_permissions(path):
    """Jobs in `path` whose GITHUB_TOKEN takes the repository default.

    Shared by the pin over the real workflows and by the synthetic pins
    in TestTheJobParserRefusesWhatItCannotRead, so those exercise this
    check rather than a second copy of it (fix round 4, T4).
    """
    if _workflow_level_permissions(path):
        return []
    return [job for job in _jobs(path)
            if not any(JOB_PERMISSIONS_RE.match(line) for line in job["lines"])]


def _workflow_jobs():
    return [(path, job) for path in _scanned_files()
            if path.parent == WORKFLOWS for job in _jobs(path)]


def test_every_job_constrains_the_github_token():
    """Fix round 3, S3: no permissions block means the repository default.

    publish.yml has always declared one per job (contents: read on build,
    id-token: write confined to the two publish jobs). ci.yml declared
    none, so its job took the repository default, which is read/write
    unless the owner has changed it, while installing and executing
    unpinned third-party packages on every branch push.
    """
    jobs = _workflow_jobs()
    by_file = {}
    for path, job in jobs:
        by_file.setdefault(path.name, set()).add(job["name"])
    # What was actually scanned, against the ledger, not against a floor
    # (fix round 4, T4). Every workflow on disk is in the ledger and the
    # ledger's job names are the ones the parser found, so a job the
    # parser stops recognising fails here as well as in _jobs().
    assert set(by_file) == {path.name for path in _scanned_files()
                            if path.parent == WORKFLOWS}
    assert by_file == WORKFLOW_JOBS, (
        f"the jobs this ledger scanned are {by_file}, the ledger says "
        f"{WORKFLOW_JOBS}. Record the change, or find out why a job is "
        f"not being read.")
    assert len(jobs) == sum(len(names) for names in WORKFLOW_JOBS.values())

    for path in {path for path, _ in jobs}:
        for job in _jobs_without_permissions(path):
            raise AssertionError(
                f"{job['where']}: job '{job['name']}' declares no "
                f"permissions block, so its GITHUB_TOKEN takes the "
                f"repository default scopes. Give it the least privilege "
                f"it needs, beside the job, the way publish.yml does.")


def test_no_checkout_persists_the_credential_it_does_not_need():
    """Fix round 3, S3: `persist-credentials: false` on every checkout.

    actions/checkout writes the job's token into .git/config by default.
    No job here pushes, fetches a submodule or uses git credentials, and
    every job installs and runs third-party code after checking out.
    """
    checkouts = []
    for path in _scanned_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        rel = _rel(path)
        for index, line in enumerate(lines):
            if "uses:" not in line or "actions/checkout@" not in line:
                continue
            where = f"{rel}:{index + 1}"
            step = []
            for following in lines[index + 1:]:
                stripped = following.strip()
                if stripped.startswith("- ") or (
                    stripped and len(following) - len(following.lstrip()) <= 2
                ):
                    break
                step.append(stripped)
            checkouts.append((where, step))

    # Anti-vacuity: the scan has to have found the checkouts that exist.
    assert len(checkouts) >= 2, checkouts
    for where, step in checkouts:
        assert "persist-credentials: false" in step, (
            f"{where}: this checkout keeps the job's GITHUB_TOKEN in "
            f".git/config for the rest of the job. Pass "
            f"persist-credentials: false unless the job really needs to "
            f"use git credentials.")


def test_every_pin_carries_the_version_its_sha_really_is():
    """The check the F5 incident needed: SHA against the tag upstream.

    A globally consistent stale comment, which is the shape Dependabot
    produced, passes every internal-consistency test in this file and
    fails this one.
    """
    pins = _pins()
    assert len(pins) >= 8, pins
    for pin in pins:
        key = (pin["action"], pin["sha"])
        assert key in VERIFIED_TAGS, (
            f"{pin['where']}: {pin['action']}@{pin['sha']} is not in "
            f"VERIFIED_TAGS. Dereference the tag against the GitHub API "
            f"(see this module's docstring) and record the pair, rather "
            f"than trusting the comment beside the pin.")
        assert VERIFIED_TAGS[key] == pin["version"], (
            f"{pin['where']}: the comment says {pin['version']} but "
            f"{pin['sha'][:12]} is the tip of "
            f"{VERIFIED_TAGS[key]} upstream.")


def test_every_action_is_sha_pinned_with_a_version_comment():
    pins = _pins()
    # Guard against a glob that matched nothing.
    assert len(pins) >= 8, pins
    assert {pin["action"] for pin in pins} == {
        "actions/checkout",
        "actions/setup-python",
        "actions/upload-artifact",
        "actions/download-artifact",
        "pypa/gh-action-pypi-publish",
        "actions/upload-pages-artifact",
        "actions/deploy-pages",
    }


def test_the_same_action_is_pinned_the_same_way_everywhere():
    by_action = {}
    for pin in _pins():
        by_action.setdefault(pin["action"], []).append(pin)
    for action, pins in by_action.items():
        shas = {pin["sha"] for pin in pins}
        versions = {pin["version"] for pin in pins}
        assert len(shas) == 1, (action, [p["where"] for p in pins], shas)
        assert len(versions) == 1, (action, [p["where"] for p in pins], versions)


# v0.15.2: the change log is read as entries, newest first: the current
# entry (the CHANGELOG's [Unreleased] part, with every fragment under
# changelog.d/ once that folder is in use), then each released entry.
# For each pinned action, the newest entry naming it at any version must
# name the version it is pinned at, so a bump is named once, in the
# current entry, and a released entry is never asked to change. The
# first "### CI" heading was read before, which a bump could pass only by
# editing a released entry. Each entry's lines are joined, so a mention
# wrapped across two lines counts.

def changelog_entries(root=REPO_ROOT):
    """[(name, text)], newest first, each text on one line."""
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    current, released = [], []
    for part in re.split(r"(?m)^(?=## \[)", text)[1:]:
        heading = part.split("\n", 1)[0].strip()
        if heading.startswith("## [Unreleased]"):
            current.append(part)
        else:
            version = heading[len("## ["):].split("]", 1)[0]
            released.append((f"the {version} entry", part))
    folder = root / "changelog.d"
    if folder.is_dir():
        current += [path.read_text(encoding="utf-8")
                    for path in sorted(folder.glob("*.md"))]
    entries = [("the current entry", "\n".join(current)), *released]
    return [(name, " ".join(body.split())) for name, body in entries]


def where_a_change_is_named(root=REPO_ROOT):
    """Where CONTRIBUTING.md's step 6 has a change described: a fragment
    once the fragments are in use (their folder, or the script that
    gathers them at release), else the [Unreleased] part."""
    if ((root / "changelog.d").is_dir()
            or (root / "scripts" / "assemble_changelog.py").is_file()):
        return "a fragment under changelog.d/"
    return "the [Unreleased] part of CHANGELOG.md"


def pins_the_changelog_misses(pins, root=REPO_ROOT):
    """A sentence for each pinned action whose newest mention in the
    change log is not the version it is pinned at, or which no entry
    names; the sentence says what to write, and where."""
    entries = changelog_entries(root)
    missed = []
    for action, version in sorted({(pin["action"], pin["version"])
                                   for pin in pins}):
        short = action.split("/")[-1]
        before = r"(?<![A-Za-z0-9-])" + re.escape(short)
        named = re.compile(before + r" v\d")
        pinned = re.compile(before + " " + re.escape(version) + r"(?!\d)")
        newest = next(((name, text) for name, text in entries
                       if named.search(text)), None)
        if newest is not None and pinned.search(newest[1]):
            continue
        found = (f"{newest[0]} names it at another version" if newest
                 else "no entry names it")
        missed.append(f"{action} is pinned at {version}, but {found}: "
                      f"name {short} {version} in "
                      f"{where_a_change_is_named(root)}")
    return missed


def test_a_pin_bump_is_read_in_the_current_entry(tmp_path):
    """Synthetic change logs, then the real one. A bump with nothing
    written is refused, saying what to write and where; written in the
    [Unreleased] part, in a fragment, or across two lines, it passes; an
    action named in no entry is refused, as is a longer version."""
    pins = [{"action": "actions/upload-artifact", "version": "v7.0.2"},
            {"action": "actions/checkout", "version": "v7.0.1"}]
    root = tmp_path / "repo"
    root.mkdir()

    def write(unreleased="", fragment=None):
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n" + unreleased
            + "\n## [0.14.2-alpha] - 2026-10-09\n\n### CI\n\n"
            "- Pins: actions/upload-artifact v7.0.1 and\n"
            "  actions/checkout v7.0.1.\n", encoding="utf-8")
        if fragment is not None:
            (root / "changelog.d").mkdir(exist_ok=True)
            (root / "changelog.d" / "bump.md").write_text(
                "### For contributors\n\n" + fragment, encoding="utf-8")

    def named(missed, *facts):
        return all(fact in missed for fact in facts)

    write()
    [missed] = pins_the_changelog_misses(pins, root)
    assert named(missed, "actions/upload-artifact", "0.14.2-alpha",
                 "upload-artifact v7.0.2", "[Unreleased]")
    write("### For contributors\n\n- actions/upload-artifact v7.0.2.\n")
    assert pins_the_changelog_misses(pins, root) == []

    write(fragment="- Nothing about the pins.\n")
    [missed] = pins_the_changelog_misses(pins, root)
    assert named(missed, "upload-artifact v7.0.2", "changelog.d/")
    assert "[Unreleased]" not in missed
    write(fragment="- The pins move: actions/upload-artifact\n  v7.0.2.\n")
    assert pins_the_changelog_misses(pins, root) == []
    # a name that only ends like an action's is not that action
    write(fragment="- upload-artifact v7.0.2; also my-checkout v2.\n")
    assert pins_the_changelog_misses(pins, root) == []

    # v7.0.20 is not v7.0.2, and it is the newest mention
    write(fragment="- actions/upload-artifact v7.0.20.\n")
    [missed] = pins_the_changelog_misses(pins, root)
    assert named(missed, "upload-artifact v7.0.2", "the current entry")
    # named nowhere at any version
    deploy = {"action": "actions/deploy-pages", "version": "v5.0.1"}
    missed = pins_the_changelog_misses(pins + [deploy], root)
    assert len(missed) == 2 and named(missed[0], "deploy-pages v5.0.1",
                                      "changelog.d/")

    # the repository's own change log names every pin
    assert pins_the_changelog_misses(_pins()) == []


class TestTheJobParserRefusesWhatItCannotRead:
    """Fix round 4, T4: the S3 permissions pin was permeable.

    `  deploy:   # staging only` and `  "deploy":` are legal YAML job
    keys that the round-3 pattern did not match, and _jobs() SKIPPED an
    unmatched line rather than refusing it. Three jobs written that way,
    two of them with no permissions block at all, passed all seven tests
    in this file: `len(jobs) >= 4` was satisfied by the jobs that did
    parse, and the per-file guard asked only that each FILE contribute a
    job. Worse, a skipped key's body was appended to the PRECEDING job,
    so one job's permissions block vouched for the next one's steps.

    These pins run the real parser over synthetic workflows, so they
    cover the spellings the repository does not happen to use.
    """

    HEADER = "name: Synthetic\non:\n  push:\njobs:\n"
    COMPLIANT = ("  test:\n"
                 "    runs-on: ubuntu-latest\n"
                 "    permissions:\n"
                 "      contents: read\n"
                 "    steps:\n"
                 "      - run: echo ok\n")

    def _write(self, tmp_path, body):
        path = tmp_path / "synthetic.yml"
        path.write_text(self.HEADER + self.COMPLIANT + body, encoding="utf-8")
        return path

    @pytest.mark.parametrize("job_key", [
        "  lint:",
        "  lint:   # style only",
        '  "lint":',
        "  'lint':",
        "  lint:  ",
    ])
    def test_a_job_spelled_any_legal_way_is_still_checked(self, tmp_path,
                                                          job_key):
        path = self._write(tmp_path,
                           f"{job_key}\n"
                           f"    runs-on: ubuntu-latest\n"
                           f"    steps:\n"
                           f"      - run: echo hi\n")
        assert [job["name"] for job in _jobs(path)] == ["test", "lint"]
        assert [job["name"] for job in _jobs_without_permissions(path)] \
            == ["lint"]

    def test_a_spelling_the_parser_cannot_read_is_refused_not_skipped(
        self, tmp_path
    ):
        """The long tail: an anchor, a flow mapping, tomorrow's surprise.

        The ledger does not have to understand every legal YAML; it has
        to fail rather than pass when it does not.
        """
        path = self._write(tmp_path,
                           "  lint: &anchor\n"
                           "    runs-on: ubuntu-latest\n"
                           "    steps:\n"
                           "      - run: echo hi\n")
        with pytest.raises(AssertionError,
                           match="is not one this ledger can read"):
            _jobs(path)

    def test_a_later_job_does_not_inherit_the_lines_of_the_one_above(
        self, tmp_path
    ):
        """The mis-attribution half: skipping the key was worse than
        missing the job, because its steps landed under the job before
        it and that job's permissions block spoke for them."""
        path = self._write(tmp_path,
                           "  lint:   # style only\n"
                           "    runs-on: ubuntu-latest\n"
                           "    steps:\n"
                           "      - run: echo hi\n")
        lines_by_job = {job["name"]: job["lines"] for job in _jobs(path)}
        assert any(JOB_PERMISSIONS_RE.match(line)
                   for line in lines_by_job["test"])
        assert not any(JOB_PERMISSIONS_RE.match(line)
                       for line in lines_by_job["lint"])
        assert any("echo hi" in line for line in lines_by_job["lint"])
        assert not any("echo hi" in line for line in lines_by_job["test"])

    def test_comments_and_blank_lines_at_job_indent_are_not_refused(
        self, tmp_path
    ):
        """The refusal must not fire on the two things that legally sit
        there and are not job keys."""
        path = self._write(tmp_path,
                           "\n"
                           "  # the style job, kept separate on purpose\n"
                           "\n"
                           "  lint:\n"
                           "    runs-on: ubuntu-latest\n"
                           "    permissions:\n"
                           "      contents: read\n"
                           "    steps:\n"
                           "      - run: echo hi\n")
        assert [job["name"] for job in _jobs(path)] == ["test", "lint"]
        assert _jobs_without_permissions(path) == []

    def test_a_workflow_level_permissions_block_still_covers_every_job(
        self, tmp_path
    ):
        """publish.yml declares per job; a workflow-level block is the
        other legal way, and the check has always accepted it."""
        path = tmp_path / "top_level.yml"
        path.write_text(
            "name: Synthetic\n"
            "on:\n"
            "  push:\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  lint:   # no block of its own\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - run: echo hi\n", encoding="utf-8")
        assert [job["name"] for job in _jobs(path)] == ["lint"]
        assert _jobs_without_permissions(path) == []
