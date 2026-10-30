#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Which tier of CI a run takes, and whether the extension's jobs run.

    python3 scripts/ci_tier.py

Run by the `tier` job, the first in .github/workflows/ci.yml, with the
runner's own Python and the standard library alone (v0.15.2; ruling 100,
item 3: less repetition in testing, the same checks).

- The fast tier is a push to a branch other than `main` and the
  integration branches, `feat/<name>`: the suite once, on Ubuntu with
  Python 3.13, and the documents job.
- Every other run is the full tier, the whole matrix: a push to `main`
  or to `feat/<name>`, a pull request, a run started by hand, and any
  event or ref this script does not know.
- On the fast tier, the desktop extension's jobs run only when the
  branch changed the packaging, the lock or a script only those jobs
  run (`EXTENSION_PATHS`), counted from where the branch left its
  integration branch: `origin/feat/<p>` for a branch `<p>/<key>` when
  that exists, else `origin/main`. A change already merged into the
  integration branch therefore does not wake them on every later piece,
  and a branch that changed one of those files keeps running them on
  each push. A file moved or renamed counts by its old path as well as
  its new one, so a move out of `packaging/` wakes them too. When git
  cannot answer, they run.

The event and the ref come from the environment (`GITHUB_EVENT_NAME`,
`GITHUB_REF`), never from a line of the workflow, and every ref reaches
git as an argument of its own, never through a shell. The answers go to
$GITHUB_OUTPUT as `fast=` and `skip_extension=`, each `true` or `false`,
and one line, the tier and why, to the step summary. The workflow
narrows a run only on an explicit `true`: an empty or missing output
runs the full matrix.
"""

import os
import subprocess
import sys
from typing import List, Mapping, Optional, Sequence, Tuple

BRANCHES = "refs/heads/"
MAIN = "main"
INTEGRATION = "feat/"
REMOTE = "refs/remotes/origin/"

# What the desktop extension's jobs build or run, beyond Exegete's own
# code: the packaging folder, the package's metadata and the lock, and
# the three scripts only those jobs run (ci.yml, the desktop-extension
# job). A path ending in "/" is a folder and counts with everything in
# it. A change to Exegete's code alone does not wake them on a piece
# branch; the integration branch's full run builds the extension every
# time.
EXTENSION_PATHS = (
    "packaging/",
    "pyproject.toml",
    "uv.lock",
    "scripts/build_desktop_extension.py",
    "scripts/smoke_desktop_extension.py",
    "scripts/extension_libraries.py",
)


class GitFailed(Exception):
    """git could not say what the branch changed; the extension's jobs run."""


def tier(event: str, ref: str) -> Tuple[bool, str]:
    """(True when the run takes the fast tier, the reason in words)."""
    if event != "push":
        return False, f"the event is {event or 'not named'}, not a push"
    if not ref.startswith(BRANCHES):
        return False, f"`{ref or 'no ref'}` is not a branch"
    branch = ref[len(BRANCHES):]
    if branch == MAIN:
        return False, "a push to `main`"
    if branch.startswith(INTEGRATION):
        return False, f"a push to the integration branch `{branch}`"
    return True, f"a push to the branch `{branch}`"


def _git(args: Sequence[str],
         cwd: Optional[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              check=False)
    except OSError as error:
        raise GitFailed(f"git could not be started: {error}") from error


def _answer(args: Sequence[str], cwd: Optional[str]) -> str:
    result = _git(args, cwd)
    if result.returncode != 0:
        said = result.stderr.decode("utf-8", "replace").strip()
        raise GitFailed(f"git {args[0]} failed: "
                        f"{said or f'exit status {result.returncode}'}")
    return result.stdout.decode("utf-8", "replace")


def base(branch: str, cwd: Optional[str] = None) -> str:
    """The ref a branch is counted from: its integration branch, when
    the branch is named `<p>/<key>` and `origin/feat/<p>` exists, else
    `origin/main`."""
    prefix, slash, _ = branch.partition("/")
    if prefix and slash:
        candidate = f"{REMOTE}{INTEGRATION}{prefix}"
        found = _git(["show-ref", "--verify", "--quiet", candidate], cwd)
        if found.returncode == 0:
            return candidate
        if found.returncode != 1:
            raise GitFailed(f"git show-ref failed: exit status "
                            f"{found.returncode}")
    return f"{REMOTE}{MAIN}"


def changed_paths(branch: str,
                  cwd: Optional[str] = None) -> Tuple[str, List[str]]:
    """(the base, every path the branch changed since it left the base)."""
    since = base(branch, cwd)
    fork = _answer(["merge-base", since, "HEAD"], cwd).strip()
    # Without --no-renames, git names a moved or renamed file by its new
    # path alone, and a move out of packaging/ would wake nothing.
    names = _answer(["-c", "core.quotepath=off", "diff", "--name-only",
                     "--no-renames", "-z", fork, "HEAD", "--"], cwd)
    return since, [name for name in names.split("\0") if name]


def wakes_extension(paths: Sequence[str]) -> List[str]:
    """The paths among `paths` that the extension's jobs build or run."""
    return [path for path in paths
            if any(path.startswith(watched) if watched.endswith("/")
                   else path == watched for watched in EXTENSION_PATHS)]


def decide(environ: Mapping[str, str],
           cwd: Optional[str] = None) -> Tuple[bool, bool, str]:
    """(fast, skip_extension, the summary line) for this run."""
    event = environ.get("GITHUB_EVENT_NAME", "")
    ref = environ.get("GITHUB_REF", "")
    fast, why = tier(event, ref)
    if not fast:
        return False, False, f"Full tier: {why}. Every job runs."
    branch = ref[len(BRANCHES):]
    try:
        since, paths = changed_paths(branch, cwd)
    except GitFailed as error:
        return True, False, (
            f"Fast tier: {why}. The desktop extension's jobs run, since "
            f"git could not say what the branch changed ({error}).")
    woken = wakes_extension(paths)
    since = since[len("refs/remotes/"):]
    if woken:
        named = ", ".join(f"`{path}`" for path in woken[:5])
        more = f" and {len(woken) - 5} more" if len(woken) > 5 else ""
        return True, False, (
            f"Fast tier: {why}. The desktop extension's jobs run: since "
            f"`{since}`, the branch changed {named}{more}.")
    return True, True, (
        f"Fast tier: {why}. The desktop extension's jobs do not run: since "
        f"`{since}`, the branch changed none of the files they build or "
        f"run.")


def main(environ: Optional[Mapping[str, str]] = None,
         cwd: Optional[str] = None) -> int:
    environ = os.environ if environ is None else environ
    fast, skip_extension, line = decide(environ, cwd)
    outputs = (f"fast={'true' if fast else 'false'}\n"
               f"skip_extension={'true' if skip_extension else 'false'}\n")
    print(line)
    if environ.get("GITHUB_OUTPUT"):
        with open(environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(outputs)
    else:
        print(outputs, end="")
    if environ.get("GITHUB_STEP_SUMMARY"):
        with open(environ["GITHUB_STEP_SUMMARY"], "a",
                  encoding="utf-8") as handle:
            handle.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
