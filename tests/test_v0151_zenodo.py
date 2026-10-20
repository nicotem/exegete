# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1, the record on Zenodo: each release is submitted to the Exeter
Data Studies community.

Zenodo's GitHub integration archives each release. When the repository
has a .zenodo.json at its root, Zenodo reads that file alone and ignores
CITATION.cff, so the file carries the full metadata and names the
community (the owner's decision of 20 October 2026). A malformed file
fails a release's archiving, and a file that drifts from CITATION.cff
gives the record other words than the citation.

Pinned here: the file parses as JSON, with no key given twice; it names
the community datastudies; it agrees with CITATION.cff on the type, the
title, the description (the abstract), the creators (family and given
names, ORCID and affiliation), the licence (in the lower case Zenodo
uses) and the keywords; it holds no version, no date and no DOI, which
Zenodo gives each release itself; it contains no em dash. The README's
badge and CITATION.cff's doi give the concept DOI, the one that always
leads to the newest release, never one release's own. CITATION.cff's
own version and date are held to the release in tests/test_updates.py.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The concept DOI: Zenodo's identifier for every version of Exegete,
# which always leads to the newest release. Each release has its own
# DOI besides (0.15.0's is 10.5281/zenodo.23496247), which would point a
# reader at an old release once the next one is out.
CONCEPT_DOI = "10.5281/zenodo.23496246"
DOI_OF_0150 = "10.5281/zenodo.23496247"


def _read(name):
    return (REPO / name).read_text(encoding="utf-8")


def _no_repeats(pairs):
    keys = [key for key, _ in pairs]
    assert len(keys) == len(set(keys)), keys
    return dict(pairs)


def _record():
    return json.loads(_read(".zenodo.json"), object_pairs_hook=_no_repeats)


# CITATION.cff is YAML; the suite has no YAML reader, and the file uses
# only plain, single-quoted and double-quoted scalars and lists of them.
def _scalar(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return json.loads(raw)
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def _citation(name):
    found = re.findall(rf"(?m)^{name}:[ \t]*(\S.*?)[ \t]*$",
                       _read("CITATION.cff"))
    assert len(found) == 1, (name, found)
    return _scalar(found[0])


def _citation_block(name):
    """The lines under a top-level key, up to the next top-level key."""
    lines = _read("CITATION.cff").splitlines()
    if f"{name}:" not in lines:
        return []
    block = []
    for line in lines[lines.index(f"{name}:") + 1:]:
        if line and not line[0].isspace():
            break
        block.append(line)
    return block


def _citation_authors():
    authors = []
    for line in _citation_block("authors"):
        item = re.match(r"\s*(-\s+)?([\w-]+):\s*(.*)$", line)
        if item:
            if item.group(1):
                authors.append({})
            authors[-1][item.group(2)] = _scalar(item.group(3))
    return authors


def _citation_keywords():
    return [_scalar(item.group(1)) for item in
            (re.match(r"\s*-\s+(.*)$", line)
             for line in _citation_block("keywords")) if item]


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


class TestTheFile:

    def test_it_is_json_with_no_key_given_twice(self):
        assert isinstance(_record(), dict)

    def test_it_names_the_community(self):
        assert {"identifier": "datastudies"} in _record()["communities"]

    def test_it_holds_no_version_and_no_date(self):
        # Zenodo takes the version and the publication date from the
        # release; a version or a date written here would be the wrong
        # one at the next release
        named = [key for key in _keys(_record())
                 if "version" in key.lower() or "date" in key.lower()]
        assert named == []

    def test_it_holds_no_doi(self):
        # Zenodo mints each release's DOI itself
        named = [key for key in _keys(_record()) if "doi" in key.lower()]
        assert named == []
        assert "10.5281/" not in _read(".zenodo.json")

    def test_it_has_no_em_dash(self):
        assert "—" not in _read(".zenodo.json")
        assert "—" not in json.dumps(_record(), ensure_ascii=False)


class TestTheFileAgreesWithTheCitation:

    def test_the_type(self):
        assert _citation("type") == "software"
        assert _record()["upload_type"] == "software"

    def test_the_title(self):
        assert _record()["title"] == _citation("title")

    def test_the_description_is_the_abstract(self):
        assert _record()["description"] == _citation("abstract")

    def test_the_creators(self):
        authors = _citation_authors()
        creators = _record()["creators"]
        assert authors and len(creators) == len(authors)
        for creator, author in zip(creators, authors):
            family, given = creator["name"].split(", ", 1)
            assert family == author["family-names"]
            assert given == author["given-names"]
            assert creator["orcid"] == author["orcid"].removeprefix(
                "https://orcid.org/")
            assert creator["affiliation"] == author["affiliation"]

    def test_the_licence(self):
        # Zenodo names licences by their SPDX identifiers in lower case
        licence = _record()["license"]
        assert licence.lower() == _citation("license").lower()
        assert licence == licence.lower()

    def test_the_keywords(self):
        assert _record().get("keywords", []) == _citation_keywords()


class TestTheConceptDoi:

    def test_the_readme_has_its_badge(self):
        badges = re.findall(
            r"\[!\[DOI\]\(https://zenodo\.org/badge/DOI/(10\.5281/[^)]+)"
            r"\.svg\)\]\(https://doi\.org/(10\.5281/[^)]+)\)",
            _read("README.md"))
        assert badges == [(CONCEPT_DOI, CONCEPT_DOI)]

    def test_the_citation_gives_it(self):
        assert _citation("doi") == CONCEPT_DOI

    def test_no_release_of_its_own_is_named(self):
        for name in ("README.md", "CITATION.cff"):
            assert DOI_OF_0150 not in _read(name), name
