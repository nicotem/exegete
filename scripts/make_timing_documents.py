#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Made-up Word files for timing how long Exegete's preview reads.

    python scripts/make_timing_documents.py --out FOLDER [--files 45]
        [--characters 360000] [--seed 15]

Writes `Timing 01.docx`, `Timing 02.docx`, ... into FOLDER (made if
missing): made-up English from a fixed word list, with no names of
people or places, in paragraphs of a few sentences. Each letter is a run
of its own, the formatting alternating between bold and italic, so that
a file is slow to read for its size, as a heavily edited document can
be. The same arguments give the same bytes: the words come from a
generator seeded with --seed and the file's number, and the archive's
parts have a fixed order and date. Standard library only.

The defaults make the corpus of v0.15.0's timing session: 45 files of
about 360,000 characters, each read in about 5 seconds on a recent Mac
(word/document.xml just under 20 MB, the limit for one part being 25).
"""

import argparse
import io
import random
import sys
import zipfile
from pathlib import Path

FIXED_DATE = (1980, 1, 1, 0, 0, 0)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# Plain words only: no names of people, places or organisations.
WORDS = (
    "about after again almost along always another answer around asked "
    "back because before began being below between both bring busy "
    "call came care carry change clear close cold could course day "
    "different does done door down during each early enough even every "
    "fact family far feel field find first follow food found friend "
    "full gave given good great group half hand hard have heard help "
    "here high hold home hope house idea important inside instead just "
    "keep kind knew know land large last later learn left less letter "
    "life light little long look made make many market matter mean "
    "might money month morning most mother much near need never next "
    "night nothing notice number often once only open other over paper "
    "part people place plan point present problem question quite rather "
    "read ready reason remember rest right road room round said same "
    "school second seemed show side since small something sometimes "
    "soon space start still story street study sure table talk tell "
    "than thing think thought through time today together told took "
    "toward town tree true turn under until upon usual very voice walk "
    "want warm watch water week went where while whole window without "
    "word work world year young"
).split()

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
    'content-types"><Default Extension="rels" ContentType="application/'
    'vnd.openxmlformats-package.relationships+xml"/><Default '
    'Extension="xml" ContentType="application/xml"/><Override '
    'PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"'
    '/></Types>')
PACKAGE_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.'
    'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>')


def sentence(rng: random.Random) -> str:
    words = [rng.choice(WORDS) for _ in range(rng.randint(6, 16))]
    if len(words) > 8 and rng.random() < 0.4:
        words[rng.randint(3, len(words) - 4)] += ","
    return " ".join(words).capitalize() + "."


def paragraphs(rng: random.Random, characters: int) -> list:
    """Paragraphs of three to seven sentences, until their text (joined
    by a blank line, as Exegete stores a Word file's) reaches
    `characters`."""
    out, total = [], 0
    while total < characters:
        text = " ".join(sentence(rng) for _ in range(rng.randint(3, 7)))
        total += len(text) + (2 if out else 0)
        out.append(text)
    return out


def _run(letter: str, bold: bool) -> str:
    look = "<w:b/><w:bCs/>" if bold else "<w:i/><w:iCs/>"
    space = ' xml:space="preserve"' if letter == " " else ""
    return f"<w:r><w:rPr>{look}</w:rPr><w:t{space}>{letter}</w:t></w:r>"


def document_xml(texts: list) -> bytes:
    body = []
    for text in texts:
        runs = "".join(_run(letter, n % 2 == 0)
                       for n, letter in enumerate(text))
        body.append(f"<w:p>{runs}</w:p>")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{W_NS}"><w:body>{"".join(body)}'
            '</w:body></w:document>').encode("utf-8")


def word_file(texts: list) -> bytes:
    parts = (("[Content_Types].xml", CONTENT_TYPES.encode("utf-8")),
             ("_rels/.rels", PACKAGE_RELS.encode("utf-8")),
             ("word/document.xml", document_xml(texts)))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in parts:
            info = zipfile.ZipInfo(name, FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data, compresslevel=9)
    return buffer.getvalue()


def make(out: Path, files: int, characters: int, seed: int) -> list:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for number in range(1, files + 1):
        rng = random.Random(seed * 1000 + number)
        path = out / f"Timing {number:02d}.docx"
        path.write_bytes(word_file(paragraphs(rng, characters)))
        written.append(path)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--files", type=int, default=45)
    parser.add_argument("--characters", type=int, default=360_000)
    parser.add_argument("--seed", type=int, default=15)
    args = parser.parse_args(argv)
    if not 1 <= args.files <= 99 or args.characters < 1:
        parser.error("--files is 1 to 99, --characters at least 1")
    for path in make(args.out, args.files, args.characters, args.seed):
        print(f"{path.name}\t{path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
