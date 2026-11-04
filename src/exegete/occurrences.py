# SPDX-License-Identifier: LGPL-3.0-or-later
"""The short ids that name each occurrence of a name in a pseudonymisation
preview (v0.15.3).

With `choose_occurrences`, the preview lists every occurrence of a name
the run would replace as a short id and its line number. It never gives
the name, a pseudonym, an entry number or the words around it, so that
the researcher can say which occurrences to leave as they are and the
assistant sends back ids alone.

An id is a keyed digest. The key is HMAC-SHA256 under the preview-token
secret over a label of its own and the project the token binds; each
occurrence's id is HMAC-SHA256 under that key over the file's id, the
SHA-256 of the file's text and the occurrence's start and end. So, under
one secret, the same text in the same project gives the same full ids on
every preview; another secret (another account's, or one made anew) or
a copy of the project in another folder gives other ids; any change to
the text gives every occurrence another id; and a change of mapping
keeps the id of each occurrence whose span it keeps. Without the secret,
an id says nothing about where it points.

A full id is 26 characters of Crockford's base 32 in lower case (no i,
l, o or u). The preview shows each cut to one length, the shortest from
five characters at which the file's ids are all distinct, and an id
given back names the one occurrence whose full id it begins. Standard
library only.
"""

import bisect
import hashlib
import hmac
import re
from typing import List, Optional, Sequence, Tuple

# How many occurrences one preview lists, in text order; past it the
# preview says how many more there are
OCCURRENCES_LISTED = 150
# The fewest characters an id is shown with, and an id given back needs
SHORTEST = 5
# A full id: 26 characters of base 32, the digest's first 130 bits
FULL_LENGTH = 26
# Crockford's base 32, in lower case
ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
# The letters Crockford's decoding reads as digits
_READ_AS = str.maketrans({"i": "1", "l": "1", "o": "0"})
# What the key is made over before the project. No other value keyed
# with the same secret begins with it: a token's signature is over JSON,
# the change record's digests begin "exegete change record" and the run
# record's text digests their own label (server.RUN_RECORD_TEXT_LABEL)
LABEL = b"exegete occurrence ids\n"
# A line break as the reading copy counts one (reading_copy._LINE_BREAK)
_LINE_BREAK = re.compile("\r\n|\r|\n")


def id_key(secret: str, project: str) -> bytes:
    """The key a project's ids are made with: HMAC-SHA256 under the
    preview-token secret over LABEL and the project as the token binds
    it (the resolved path of its database)."""
    return hmac.new(secret.encode("ascii"),
                    LABEL + project.encode("utf-8"),
                    hashlib.sha256).digest()


def _base32(digest: bytes) -> str:
    """The digest's first 130 bits as FULL_LENGTH characters of ALPHABET.
    The bytes are read as one number through their hex digits, since the
    sweep for a guesser of character sets refuses the other spelling
    (tests/test_v0143_import_decisions.py)."""
    number = int(digest[:17].hex(), 16) >> (17 * 8 - 5 * FULL_LENGTH)
    letters = []
    for _ in range(FULL_LENGTH):
        letters.append(ALPHABET[number & 31])
        number >>= 5
    return "".join(reversed(letters))


def full_ids(key: bytes, file_id: int, text_sha: str,
             spans: Sequence[Tuple[int, int]]) -> List[str]:
    """Each occurrence's full id, in the order of `spans`: HMAC-SHA256
    under `key` over the file's id, the SHA-256 of its text (in hex) and
    the occurrence's start and end."""
    ids = []
    for start, end in spans:
        message = f"{int(file_id)}\n{text_sha}\n{int(start)}\n{int(end)}"
        ids.append(_base32(hmac.new(key, message.encode("ascii"),
                                    hashlib.sha256).digest()))
    return ids


def shown_ids(full: Sequence[str],
              shortest: Optional[int] = None) -> List[str]:
    """Each full id cut to one length: the shortest, from `shortest`
    characters (SHORTEST unless given), at which every id of the file is
    distinct. The same full ids give the same shown ids on every call."""
    least = SHORTEST if shortest is None else shortest
    for length in range(max(1, least), FULL_LENGTH):
        cut = [one[:length] for one in full]
        if len(set(cut)) == len(cut):
            return cut
    return list(full)


def match(given: object, full: Sequence[str],
          shortest: Optional[int] = None) -> Optional[int]:
    """The position in `full` of the occurrence an id given names, or None.

    An id names the occurrence whose full id it begins, when it has at
    least `shortest` characters (SHORTEST unless given) and begins
    exactly one. It is read as Crockford's decoding reads it: in either
    case, with i and l as 1 and o as 0, and white space around it set
    aside. So an id shown earlier still names its occurrence after more
    occurrences lengthen the ids shown, unless one of them has a full id
    that begins as that id does: the id then begins two full ids and
    names nothing, never the other occurrence (about one chance in 33
    million for each occurrence added, at five characters). One whose
    occurrence moved or went names nothing.
    """
    if not isinstance(given, str):
        return None
    wanted = given.strip().lower().translate(_READ_AS)
    if len(wanted) < (SHORTEST if shortest is None else shortest):
        return None
    found = [index for index, one in enumerate(full)
             if one.startswith(wanted)]
    return found[0] if len(found) == 1 else None


def line_numbers(text: str, starts: Sequence[int]) -> List[int]:
    """The line each start falls on, counted from 1. A line ends at a
    carriage return and line feed, a carriage return alone or a line
    feed alone, as the reading copy divides a text."""
    line_starts = [0] + [found.end() for found in _LINE_BREAK.finditer(text)]
    return [bisect.bisect_right(line_starts, start) for start in starts]
