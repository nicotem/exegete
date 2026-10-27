#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Check the releases in the locks against the published advisories (v0.15.1).

    python scripts/check_advisories.py uv.lock
    python scripts/check_advisories.py uv.lock \
        packaging/desktop-extension/validator/package-lock.json
    python scripts/check_advisories.py uv.lock --answer saved.json

Every package in each lock given that comes from a registry, each of
its locked releases (cryptography has three, one per group of
computers), is asked of OSV (https://osv.dev), the open database that
gathers GitHub's advisories and the Python Packaging Authority's, in
one request to
https://api.osv.dev/v1/querybatch: the libraries' names and releases,
nothing else, and no credentials. A request that fails is tried once
more after 30 seconds. A lock's registry comes from its name (v0.15.2):
`uv.lock`, Exegete's libraries, from PyPI; `package-lock.json`, the
libraries of the official validator CI installs to check the desktop
extension's manifest (packaging/desktop-extension/validator), from npm.
A lock of any other name is not read.

An advisory already read and accepted is in KNOWN below, or KNOWN_NPM
for the validator's, with the library and releases it was found
against, the date it was accepted and why. Each one still reported is
a notice; each new one, or a known one reported against another
release, is an error; an accepted one no longer reported is a notice
saying its entry can go, so that the list is pruned rather than left to
grow. Only the entries of the registries asked are read, so a run given
uv.lock alone never says that the validator's can go. Under GitHub
Actions these are ::notice and ::error lines, and a table goes to the
step summary.

Exits 0 when every advisory reported is known, 1 on a new one, and 2
when the check cannot be made: a lock unreadable, of another name or
form, or with no package from a registry, OSV not reached, or its
answer not complete. `--answer FILE` reads a saved answer in place of
the request (the tests). Standard library only (tomllib, from Python
3.11; on 3.10 the tomli that pytest brings, for the tests), so CI runs
it without installing anything; the weekly workflow is
.github/workflows/advisories.yml.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

OSV_URL = "https://api.osv.dev/v1/querybatch"
REQUEST_TIMEOUT_SECONDS = 60
RETRY_AFTER_SECONDS = 30

# The registry each lock's releases come from, by the lock's name, as OSV
# names it (v0.15.2).
REGISTRIES = {"uv.lock": "PyPI", "package-lock.json": "npm"}
NPM_REGISTRY = "https://registry.npmjs.org/"

# The two cryptography releases the lock keeps for two groups of
# computers (uv.lock, [manifest] and the three cryptography entries):
# the last with a ready-made package for Intel Macs (48.0.1) and for
# Windows on Arm (46.0.3), so that installing Exegete there never has to
# build it. The MCP library brings cryptography through PyJWT; Exegete
# never loads it (importing Exegete's server loads neither).
CRYPTOGRAPHY_HELD = (
    "the last cryptography release with a ready-made package for Intel "
    "Macs (48.0.1) or Windows on Arm (46.0.3), kept in the lock for those "
    "computers alone; Exegete never loads cryptography")

# advisory id -> (library, releases it was found against, the date it
# was accepted, why). The first entries were accepted when the lock of
# 13 October 2026 kept these two releases, with 6 records against
# 48.0.1 and 13 against 46.0.3 (its security review); their ids were
# read again on 20 October, the same 19, each published before 13
# October. The comment gives each one's subject and its first fixed
# release.
_BOTH = ("48.0.1", "46.0.3")
_WINDOWS_ON_ARM = ("46.0.3",)
KNOWN: Dict[str, Tuple[str, Tuple[str, ...], str, str]] = {
    # PKCS#7 decryption, an oracle (50.0.0)
    "GHSA-g6cj-pr64-35w5": ("cryptography", _BOTH, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    "PYSEC-2026-3552": ("cryptography", _BOTH, "2026-10-13",
                        CRYPTOGRAPHY_HELD),
    # certificate path building, exponential (49.0.0)
    "GHSA-jwv3-5hgf-82ww": ("cryptography", _BOTH, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    "PYSEC-2026-3553": ("cryptography", _BOTH, "2026-10-13",
                        CRYPTOGRAPHY_HELD),
    # wildcard names and name constraints (49.0.0)
    "GHSA-m2h6-j472-rp4c": ("cryptography", _BOTH, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    "PYSEC-2026-3554": ("cryptography", _BOTH, "2026-10-13",
                        CRYPTOGRAPHY_HELD),
    # the OpenSSL in the ready-made packages (48.0.1)
    "GHSA-537c-gmf6-5ccf": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    # name constraints on peer names (46.0.6)
    "GHSA-m959-cc7f-wv43": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    "PYSEC-2026-35": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                      CRYPTOGRAPHY_HELD),
    # a buffer overflow with non-contiguous buffers (46.0.7)
    "GHSA-p423-j2cm-9vmq": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    "PYSEC-2026-36": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                      CRYPTOGRAPHY_HELD),
    # subgroup validation for binary curves (46.0.5)
    "GHSA-r6ph-v2qm-q3c2": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                            CRYPTOGRAPHY_HELD),
    "PYSEC-2026-2141": ("cryptography", _WINDOWS_ON_ARM, "2026-10-13",
                        CRYPTOGRAPHY_HELD),
}

# The official validator's libraries (v0.15.2): CI installs them, with
# their install scripts off (`npm ci --ignore-scripts`), to check the
# manifest of the desktop extension Exegete built; Exegete installs none.
VALIDATOR_ONLY = (
    "a library of the official validator, which CI alone installs, with "
    "its install scripts off, to check the manifest of the extension "
    "Exegete built; Exegete installs none of them")

# advisory id -> (library, releases, the date accepted, why), as KNOWN,
# for packaging/desktop-extension/validator/package-lock.json: the four
# OSV reported when that lock joined this check, on 27 October 2026. The
# comment gives each one's subject and its first fixed release.
KNOWN_NPM: Dict[str, Tuple[str, Tuple[str, ...], str, str]] = {
    # RSA signatures forged (none fixed yet; 1.4.0 the last affected)
    "GHSA-86w9-cpqp-85rv": ("node-forge", ("1.4.0",), "2026-10-27",
                            VALIDATOR_ONLY),
    # a temporary file written through a symbolic link (0.2.4)
    "GHSA-52f5-9888-hmc6": ("tmp", ("0.0.33",), "2026-10-27",
                            VALIDATOR_ONLY),
    # a path out of the temporary folder through its prefix (0.2.6)
    "GHSA-ph9p-34f9-6g65": ("tmp", ("0.0.33",), "2026-10-27",
                            VALIDATOR_ONLY),
    # memory exhausted by oversized collections (4.6.6)
    "GHSA-mrhx-c7xc-m3w5": ("zod", ("3.25.76",), "2026-10-27",
                            VALIDATOR_ONLY),
}


@dataclass(frozen=True)
class Finding:
    registry: str
    library: str
    release: str
    advisory: str


class CannotCheck(Exception):
    """The check could not be made (exit 2)."""


# ---------------------------------------------------------------------------
# The lock, and the request
# ---------------------------------------------------------------------------

def registry_of(lock_path: Path) -> str:
    """The registry a lock's releases come from, by the lock's name."""
    registry = REGISTRIES.get(lock_path.name)
    if registry is None:
        raise CannotCheck(f"{lock_path} is not a lock this check reads: "
                          f"only uv.lock (PyPI) and package-lock.json (npm)")
    return registry


def locked_releases(lock_path: Path) -> List[Tuple[str, str]]:
    """(name, version) of every package from a registry, in the lock's
    order; a library locked at several releases gives one pair each."""
    if registry_of(lock_path) == "npm":
        return _npm_releases(lock_path)
    try:
        with open(lock_path, "rb") as handle:
            lock = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise CannotCheck(f"cannot read the lock {lock_path}: {error}")
    pairs = []
    for package in lock.get("package", []):
        source = package.get("source", {})
        if "registry" in source:
            pairs.append((package["name"], package["version"]))
    if not pairs:
        raise CannotCheck(f"the lock {lock_path} has no package from a "
                          f"registry")
    return pairs


def _npm_releases(lock_path: Path) -> List[Tuple[str, str]]:
    """package-lock.json, of lockfileVersion 3 alone: each entry under
    node_modules/ resolved from npm's registry, named by the part after
    the last node_modules/, so a scoped name keeps its scope."""
    try:
        with open(lock_path, "rb") as handle:
            lock = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise CannotCheck(f"cannot read the lock {lock_path}: {error}")
    if (not isinstance(lock, dict) or lock.get("lockfileVersion") != 3
            or not isinstance(lock.get("packages"), dict)):
        raise CannotCheck(f"the lock {lock_path} is not of lockfileVersion "
                          f"3, the only form this check reads")
    pairs = []
    for path, package in lock["packages"].items():
        under = path.startswith("node_modules/") or "/node_modules/" in path
        if not under or not isinstance(package, dict):
            continue
        if not str(package.get("resolved", "")).startswith(NPM_REGISTRY):
            continue
        version = package.get("version")
        if not isinstance(version, str) or not version:
            raise CannotCheck(f"the lock {lock_path} gives no release for "
                              f"{path}")
        pairs.append((path.rsplit("node_modules/", 1)[1], version))
    if not pairs:
        raise CannotCheck(f"the lock {lock_path} has no package from a "
                          f"registry")
    return pairs


def request_body(queries: Sequence[Tuple[str, str, str]]) -> bytes:
    """One request for every lock: each (registry, name, version) asked
    in its own registry, in order."""
    body = [{"package": {"name": name, "ecosystem": registry},
             "version": version} for registry, name, version in queries]
    return json.dumps({"queries": body}).encode("utf-8")


def ask_osv(body: bytes, opener: Callable = urllib.request.urlopen,
            sleep: Callable[[float], None] = time.sleep) -> dict:
    """OSV's answer to one querybatch request, tried once more after
    RETRY_AFTER_SECONDS when it fails."""
    request = urllib.request.Request(
        OSV_URL, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "User-Agent": "exegete-advisory-check"})
    error: Optional[BaseException] = None
    for attempt in range(2):
        if attempt:
            sleep(RETRY_AFTER_SECONDS)
        try:
            with opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as answer:
                return json.loads(answer.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as caught:
            error = caught
    raise CannotCheck(f"OSV was not reached, or gave no answer that could "
                      f"be read ({OSV_URL}), twice, 30 seconds apart: "
                      f"{error}")


def findings_of(queries: Sequence[Tuple[str, str, str]],
                answer: dict) -> List[Finding]:
    """Each advisory OSV reports, with the release it was asked about.
    The answer's results follow the queries' order, one each."""
    results = answer.get("results") if isinstance(answer, dict) else None
    if not isinstance(results, list) or len(results) != len(queries):
        raise CannotCheck(
            f"OSV's answer does not hold one result for each of the "
            f"{len(queries)} releases asked about")
    found = []
    for (registry, name, version), result in zip(queries, results):
        if not isinstance(result, dict):
            raise CannotCheck(f"OSV's answer for {name} {version} is not "
                              f"readable")
        if result.get("next_page_token"):
            raise CannotCheck(f"OSV's answer for {name} {version} is in "
                              f"pages, and only the first came")
        vulns = result.get("vulns") or []
        if not isinstance(vulns, list) or not all(
                isinstance(vuln, dict) and vuln.get("id") for vuln in vulns):
            raise CannotCheck(f"OSV's answer for {name} {version} is not "
                              f"readable")
        found += [Finding(registry, name, version, str(vuln["id"]))
                  for vuln in vulns]
    return found


# ---------------------------------------------------------------------------
# Known, new, and no longer reported
# ---------------------------------------------------------------------------

def known_for(registries) -> Dict[str, Tuple[str, Tuple[str, ...], str,
                                             str]]:
    """The accepted advisories of the registries asked, gathered at the
    call, so that a test's replacement of KNOWN holds."""
    gathered = {}
    if "PyPI" in registries:
        gathered.update(KNOWN)
    if "npm" in registries:
        gathered.update(KNOWN_NPM)
    return gathered


def _list_of(advisory: str) -> str:
    """The name of the list an accepted advisory is written in."""
    return "KNOWN_NPM" if advisory in KNOWN_NPM else "KNOWN"


def sort_out(found: Sequence[Finding], known=None):
    """(known findings, new findings, known ids no longer reported)."""
    known = KNOWN if known is None else known
    accepted, new = [], []
    for finding in found:
        entry = known.get(finding.advisory)
        if (entry and entry[0] == finding.library
                and finding.release in entry[1]):
            accepted.append(finding)
        else:
            new.append(finding)
    reported = {finding.advisory for finding in accepted}
    gone = sorted(advisory for advisory in known if advisory not in reported)
    return accepted, new, gone


def _escape(message: str) -> str:
    return (message.replace("%", "%25").replace("\r", "%0D")
            .replace("\n", "%0A"))


def report_lines(accepted, new, gone, known=None,
                 actions: bool = False) -> List[str]:
    """The new ones first, so that they stay within the annotations
    GitHub shows for a step; then the known ones no longer reported,
    then the known ones."""
    known = KNOWN if known is None else known
    lines = []
    for finding in new:
        text = f"{finding.library} {finding.release}: {finding.advisory}"
        lines.append(f"::error title=New advisory::{_escape(text)}"
                     if actions else f"NEW: {text}")
    for advisory in gone:
        library, releases, _, _ = known[advisory]
        text = (f"{advisory} ({library} {', '.join(releases)}) is no "
                f"longer reported: its entry in {_list_of(advisory)} can go")
        lines.append(f"::notice title=Advisory no longer reported::"
                     f"{_escape(text)}" if actions else f"gone: {text}")
    for finding in accepted:
        _, _, date, reason = known[finding.advisory]
        text = (f"{finding.library} {finding.release}: {finding.advisory}, "
                f"known since {date}: {reason}")
        lines.append(f"::notice title=Known advisory::{_escape(text)}"
                     if actions else f"known: {text}")
    return lines


def summary_line(queries, accepted, new, gone) -> str:
    each: Dict[str, int] = {}
    for registry, _, _ in queries:
        each[registry] = each.get(registry, 0) + 1
    registries = ", ".join(f"{count} {registry}"
                           for registry, count in each.items())
    return (f"{len(queries)} locked releases asked of OSV ({registries}): "
            f"{len(accepted) + len(new)} advisories reported, "
            f"{len(new)} new, {len(accepted)} known; "
            f"{len(gone)} known no longer reported")


def write_step_summary(path: str, line: str, accepted, new, gone,
                       known=None) -> None:
    known = KNOWN if known is None else known
    out = ["### Advisories against the locked releases", "", line, ""]
    rows = ([(f, "new") for f in new]
            + [(f, f"known since {known[f.advisory][2]}") for f in accepted])
    if rows:
        out += ["| Registry | Library | Release | Advisory | |",
                "|---|---|---|---|---|"]
        out += [f"| {f.registry} | {f.library} | {f.release} | "
                f"{f.advisory} | {status} |" for f, status in rows]
        out.append("")
    if gone:
        out += ["Known, no longer reported (their entries can go): "
                + ", ".join(gone), ""]
    with open(path, "a", encoding="utf-8") as summary:
        summary.write("\n".join(out) + "\n")


def main(argv: Optional[List[str]] = None, opener=None, sleep=None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the releases in uv.lock and package-lock.json "
                    "against OSV's advisories.")
    parser.add_argument("locks", nargs="+", type=Path, metavar="lock",
                        help="uv.lock (PyPI) or package-lock.json (npm)")
    parser.add_argument("--answer", type=Path,
                        help="a saved OSV answer, read in place of the "
                             "request")
    args = parser.parse_args(argv)
    try:
        queries = []
        for lock in args.locks:
            registry = registry_of(lock)
            queries += [(registry, name, version)
                        for name, version in locked_releases(lock)]
        if args.answer:
            try:
                answer = json.loads(args.answer.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise CannotCheck(f"cannot read the answer {args.answer}: "
                                  f"{error}")
        else:
            answer = ask_osv(request_body(queries),
                             opener=opener or urllib.request.urlopen,
                             sleep=sleep or time.sleep)
        found = findings_of(queries, answer)
    except CannotCheck as error:
        print(f"check_advisories: {error}", file=sys.stderr)
        return 2
    known = known_for({registry for registry, _, _ in queries})
    accepted, new, gone = sort_out(found, known)
    actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for line in report_lines(accepted, new, gone, known, actions=actions):
        print(line)
    line = summary_line(queries, accepted, new, gone)
    print(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        write_step_summary(os.environ["GITHUB_STEP_SUMMARY"], line,
                           accepted, new, gone, known)
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
