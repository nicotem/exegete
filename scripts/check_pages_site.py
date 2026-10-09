#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Check the update site in pages/ against this release.

    python scripts/check_pages_site.py [--tag TAG] [--live]

The site is what every installed copy with checking on relies on:
`latest.json`, which it fetches from updates.VERSION_FILE_URL, and the
update page its notes and answers link to (updates.UPDATE_PAGE). It is
published by .github/workflows/pages.yml, deployed from GitHub Actions
and never from a branch (the owner's decision of 5 October 2026,
docs/update-check/design.md, D3), and that workflow runs this script
first. The test suite runs the same checks without --tag or --live
(tests/test_v0142_pages.py), so a release prepared with last release's
site fails before it is tagged.

What it checks, offline:
- the site holds latest.json, index.html and update/index.html, and
  nothing else;
- latest.json is the version file Exegete accepts
  (updates.parse_version_file), naming this release: the version is
  release.VERSION, the date release.RELEASED;
- the update page names the release in both spellings, its date, its
  summary (release.SUMMARY), its download link and its notes, in the
  links Exegete builds itself (updates.download_link,
  updates.release_notes_link);
- both pages load nothing from another site and run no script, and link
  only to the site itself and to the repository on GitHub.

With --tag, that the tag is this release's (v<release.VERSION>), so the
site is published only from a release. With --live, which reaches the
network and is for the workflow only, that the version file now live is
not newer than this one: publishing an earlier release's site would
send every copy back to it. No file live yet (the first publication)
is allowed.

Prints each problem and exits 1, or prints what it checked and exits 0.
Needs only the standard library and src/ on the path.
"""

import argparse
import html
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from exegete import release, updates  # noqa: E402

SITE = REPO / "pages"
FILES = ("index.html", "latest.json", "update/index.html")
# The only places the pages may link to, besides themselves
ALLOWED_LINKS = ("https://github.com/nicotem/exegete/",
                 "https://github.com/nicotem/exegete\"")
_HREF = re.compile(r"""\bhref\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_LOADS = re.compile(r"<script|<link\b|<img\b|<iframe|\bsrc\s*=|@import|"
                    r"url\(", re.IGNORECASE)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def this_release() -> updates.Version:
    """release.VERSION as the version file spells it (0.14.2a0)."""
    for candidate in _pep440_candidates(release.VERSION):
        version = updates.parse_published(candidate)
        if version is not None and version.display() == release.VERSION:
            return version
    raise SystemExit(f"release.VERSION {release.VERSION!r} is not a "
                     f"version the version file can name")


def _pep440_candidates(display: str) -> List[str]:
    match = re.fullmatch(r"([0-9.]+)(?:-(alpha|beta|rc)(?:\.([0-9]+))?)?",
                         display)
    if not match:
        return []
    base, pre, number = match.groups()
    if pre is None:
        return [base]
    short = {"alpha": "a", "beta": "b", "rc": "rc"}[pre]
    return [f"{base}{short}{number or 0}"]


def _words(page: str) -> str:
    """The page's text as a reader sees it: no tags, entities read,
    white space made single."""
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", page)).split())


def check_site(site: Path = SITE, today: Optional[date] = None
               ) -> List[str]:
    """Every problem with the site in `site`, offline; [] when none."""
    today = _today() if today is None else today
    problems: List[str] = []
    found = sorted(p.relative_to(site).as_posix()
                   for p in site.rglob("*") if p.is_file())
    if found != sorted(FILES):
        problems.append(f"the site holds {found}, not {sorted(FILES)}")
    try:
        raw = (site / "latest.json").read_bytes()
    except OSError as error:
        return problems + [f"latest.json cannot be read: {error}"]
    try:
        published = updates.parse_version_file(raw, today)
    except updates.CheckFailed as failure:
        return problems + [f"latest.json is refused by Exegete: "
                           f"{failure.kind}"]
    version = this_release()
    if published.version != version:
        problems.append(f"latest.json names {published.version.pep440()}, "
                        f"this release is {version.pep440()}")
    if published.released.isoformat() != release.RELEASED:
        problems.append(f"latest.json is dated {published.released}, "
                        f"release.RELEASED is {release.RELEASED}")
    display = version.display()
    pages = {}
    for name in ("index.html", "update/index.html"):
        try:
            pages[name] = (site / name).read_text(encoding="utf-8")
        except OSError as error:
            problems.append(f"{name} cannot be read: {error}")
    for name, text in pages.items():
        if _LOADS.search(text):
            problems.append(f"{name} loads or runs something: "
                            f"{_LOADS.search(text).group(0)}")
        for link in _HREF.findall(text):
            if "://" not in link and not link.startswith("mailto:"):
                continue                       # on the site itself
            if not (link + '"').startswith(ALLOWED_LINKS):
                problems.append(f"{name} links to {link}")
    update_page = pages.get("update/index.html", "")
    links = [html.unescape(link) for link in _HREF.findall(update_page)]
    for what, link in (("the download link", updates.download_link(display)),
                       ("the release notes",
                        updates.release_notes_link(display))):
        if link not in links:
            problems.append(f"update/index.html does not link {what}: "
                            f"{link}")
    page = _words(update_page)
    for what, words in (
            ("the version", f"The newest version is {display}, from "
                            f"{updates.spoken_date(published.released)}."),
            ("the summary", f"What's new: {' '.join(release.SUMMARY.split())}"),
            ("the file's name", f"exegete-{display}.mcpb"),
            ("the version pip installs",
             f'"exegete=={version.pep440()}"'),
            ("the version uvx runs", f"exegete@{version.pep440()}"),
            ("the tag", f"git merge --ff-only v{display}")):
        if words not in page:
            problems.append(f"update/index.html does not give {what}: "
                            f"{words}")
    return problems


def check_tag(tag: str) -> List[str]:
    expected = f"v{release.VERSION}"
    return [] if tag == expected else [
        f"the site is published from this release's tag, {expected}, "
        f"not from {tag!r}"]


def check_live(today: Optional[date] = None) -> List[str]:
    """The version file live now is not newer than this release's.
    Reaches the network: for the workflow only."""
    today = _today() if today is None else today
    try:
        live = updates.parse_version_file(updates.fetch(), today)
    except updates.CheckFailed as failure:
        if failure.kind == updates.REFUSED:
            print("No version file is live yet (the website refused): "
                  "this is the first publication.")
            return []
        return [f"the live version file could not be read "
                f"({failure.kind}); try again later"]
    if live.version.key() > this_release().key():
        return [f"the live version file names {live.version.display()}, "
                f"newer than this release, {release.VERSION}: publishing "
                f"would send every copy back to an earlier version"]
    print(f"Live now: {live.version.display()}.")
    return []


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tag", help="the tag the workflow runs from")
    parser.add_argument("--live", action="store_true",
                        help="compare with the version file live now "
                             "(reaches the network)")
    args = parser.parse_args(argv)
    problems = check_site()
    if args.tag is not None:
        problems += check_tag(args.tag)
    if args.live and not problems:
        problems += check_live()
    for problem in problems:
        print(f"Problem: {problem}")
    if problems:
        return 1
    print(f"The site is {release.VERSION}'s, dated {release.RELEASED}: "
          f"{', '.join(FILES)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
