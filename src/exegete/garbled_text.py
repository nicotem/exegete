# SPDX-License-Identifier: LGPL-3.0-or-later
"""Letters that came out wrong in a file itself (0.14.3).

A UTF-8 file opened once in another character set and saved again carries
its letters as other characters: "é" becomes "Ã©" through Windows
Western, "√©" through the Mac's own Western set, "Ă©" through Windows
Central European; "П" becomes "Рџ" through Windows Cyrillic; "’" becomes
"â€™" or "‚Äô". A name written that way escapes the names list, so the
import warns of such a file and brings it in only on the researcher's
word (`doc_import.evaluate`; the owner's ruling of 7 October 2026). What
follows finds signs, not proof: correct text can show one, and a
garbled file can show none.

How the signs are read. In each set below, every character a byte from
0x80 to 0xFF stands for either starts a UTF-8 character or continues one.
A run of characters shaped like UTF-8 in a set is read back through it,
and the reading back is weighed against the characters as written, each
between the same two neighbours. The run is a sign only when the reading
back is the less odd. Correct text writes runs of that shape too ("é",
a long dash and a closing quotation mark, a transcript's "José" cut
off), and they read back into something odder ("閔" inside a word). What
makes a reading odd:

- a capital straight after a small letter ("JosÃ©");
- a symbol inside or against a word ("Ã©", "√®"), or between other
  characters with no space ("5¬†anys");
- punctuation glued between letters, other than an apostrophe, a
  hyphen, a middle dot or a dash ("WÄ…sik", "d‚Äôhabitude"), an
  ellipsis counting half;
- letters and other characters alternating more than twice with no
  space ("„Ç™„Éï");
- letters of two scripts side by side, or on either side of a joining
  mark ("Г–PNV"), Latin beside Chinese, Japanese or Korean counting
  half (they meet without a space in those languages);
- a letter rare in running text (IPA, modifier letters, the rarer Latin
  Extended-B letters, the CJK extension blocks);
- "Ã" before a letter other than A to Z ("ÃŠTRE").

A reading back cannot stand at all (and the run is no sign) when it
gives a control, private-use or unassigned character, a mark with no
letter of its script before it, a letter of another script against a
letter of the word (other than Latin beside Chinese, Japanese or
Korean), or punctuation of another script inside a word.

The sets: Windows' own (Western, Central European, Cyrillic, Greek,
Turkish, Hebrew, Arabic, Baltic, Vietnamese), the Mac's (Western,
Central European, Cyrillic, Greek, Icelandic), DOS's (437, 850, 852,
866), KOI8-R and KOI8-U, and Shift JIS's half-width katakana ("Agnﾃｨs"
for "Agnès"). Latin-1 reads a Western letter as Windows Western does,
so it is read back through that set, and leaves a C1 control character
(a sign on its own, as is the replacement character) where Windows
Western has a letter or a symbol. The other ISO sets are not read back:
what they make of a letter ("JosĂŠ" for "José" through ISO 8859-2) is a
sign only where it holds such a control character. GBK is read too,
where one character stands for a two-byte UTF-8 one ("Agn猫s"); that is
how about one Chinese character in seven is written, so GBK's runs need
a clearer sign (odder by two as written than read back), or three or
more characters reading back as one word of Cyrillic, Greek, Hebrew,
Arabic or Armenian. Big5, EUC-KR and EUC-JP are not read: their runs
are ordinary Chinese ("的" between two Latin words reads back as a
Latin letter through EUC-JP).

Measured on correct text (QualCoder 4.0's translations, LibreOffice's
autocorrect lists and contributors' names, Word's and LibreOffice's
interface strings, macOS's own translations: about two million distinct
strings in some 60 languages), no string was a sign except strings
garbled themselves (holding a control character, or LibreOffice's
autocorrect entry for "Â¢"). Read once through each set, those strings
were signs 92 to 100 times in a hundred through each single-byte set,
80 through GBK and 71 through Shift JIS, a string at a time; a whole
file has many more chances. The third checks of 7 October 2026 found
more on both sides. Missed, however many times it stands in a file: a
garbled letter that reads as natural where it stands ("ĆØ" for the
Italian word "è" through Windows Baltic, "Ã" and a no-break space for
"à"); a garbled capital at a word's start through the Western and
Central European sets ("Ã–zdemir", "ÄŒapek", "Åšliwa"); single letters
of a name through Windows Central European ("MĂĽller", "JĂłzef"); most
garbled letters at a word's start or end through GBK ("Jos茅"), and
every character UTF-8 writes in three bytes through it ("don鈥檛");
two marks between letters ("Nguyá»…n"); garbled punctuation outside
any word. Signs in correct text: Chinese with English words written
inside it ("这个project太tough了"), a sum straight after an opening
quotation mark or in a range ("‘£5", "£5–£10"), a capital inside a
Cyrillic word ("ПриватБанк"), Arabic punctuation typed straight before
the next word, an ellipsis typed straight before a word, box drawing.
Hence the researcher's word, after a look at the places marked.

The cost is one scan a set and a few small steps a run, and the same
run between the same neighbours is weighed once, so a file costs about
what its length does.
"""

import bisect
import re
import unicodedata
from typing import Dict, Iterator, List, NamedTuple, Optional, Pattern, Tuple

# Read back through each of these; Latin-1 through Windows Western and
# the C1 sign, the other ISO sets through the C1 sign alone.
SINGLE_BYTE_SETS = (
    "cp1252", "cp1250", "cp1251", "cp1253", "cp1254", "cp1255", "cp1256",
    "cp1257", "cp1258", "mac_roman", "mac_latin2", "mac_cyrillic",
    "mac_greek", "mac_iceland", "cp437", "cp850", "cp852", "cp866",
    "koi8_r", "koi8_u",
    # Only its half-width katakana are single bytes; the table below
    # keeps those alone.
    "shift_jis")


def _class(chars) -> str:
    return "[" + "".join("\\U%08x" % ord(c) for c in sorted(set(chars))) \
        + "]"


def _units() -> List[Tuple[str, Pattern]]:
    """Each set's runs shaped like UTF-8: GBK's characters that stand for
    a two-byte UTF-8 character, then, for each single-byte set, a byte
    from 0xC2 to 0xDF, 0xE0 to 0xEF or 0xF0 to 0xF4 followed by one, two
    or three from 0x80 to 0xBF, as the set writes them."""
    out = []
    pieces = []
    for a in range(0xC2, 0xE0):
        for b in range(0x80, 0xC0):
            try:
                pieces.append(bytes([a, b]).decode("gbk"))
            except UnicodeDecodeError:
                pass
    out.append(("gbk", _class(pieces)))
    for name in SINGLE_BYTE_SETS:
        table = {}
        for b in range(0x80, 0x100):
            try:
                ch = bytes([b]).decode(name)
            except UnicodeDecodeError:
                continue
            if len(ch) == 1 and ord(ch) >= 0x80:
                table[b] = ch
        cont = _class(c for b, c in table.items() if b <= 0xBF)
        lead2 = [c for b, c in table.items() if 0xC2 <= b <= 0xDF]
        lead3 = [c for b, c in table.items() if 0xE0 <= b <= 0xEF]
        lead4 = [c for b, c in table.items() if 0xF0 <= b <= 0xF4]
        forms = []
        if lead2:
            forms.append(_class(lead2) + cont)
        if lead3:
            forms.append(_class(lead3) + cont + "{2}")
        if lead4:
            forms.append(_class(lead4) + cont + "{3}")
        out.append((name, "(?:" + "|".join(forms) + ")"))
    return [(name, re.compile(unit + "+")) for name, unit in out]


_UNITS = _units()
_C1_OR_REPLACEMENT = re.compile("[\u0080-\u009f\ufffd]")

# Scripts, by block, for letters, marks and the punctuation of a script.
# None: no script of its own (combining accents, modifier letters, the
# ordinal indicators, the micro sign).
_SCRIPTS = (
    (0x00AA, 0x00AA, None), (0x00B5, 0x00B5, None), (0x00BA, 0x00BA, None),
    (0x00C0, 0x02AF, "Latin"), (0x02B0, 0x036F, None),
    (0x0370, 0x03FF, "Greek"), (0x0400, 0x052F, "Cyrillic"),
    (0x0530, 0x058F, "Armenian"), (0x0590, 0x05FF, "Hebrew"),
    (0x0600, 0x06FF, "Arabic"), (0x0700, 0x074F, "Syriac"),
    (0x0750, 0x077F, "Arabic"), (0x0780, 0x07BF, "Thaana"),
    (0x07C0, 0x07FF, "NKo"), (0x0800, 0x085F, "Samaritan"),
    (0x0860, 0x086F, "Syriac"), (0x0870, 0x08FF, "Arabic"),
    (0x0900, 0x097F, "Devanagari"), (0x0980, 0x09FF, "Bengali"),
    (0x0A00, 0x0A7F, "Gurmukhi"), (0x0A80, 0x0AFF, "Gujarati"),
    (0x0B00, 0x0B7F, "Oriya"), (0x0B80, 0x0BFF, "Tamil"),
    (0x0C00, 0x0C7F, "Telugu"), (0x0C80, 0x0CFF, "Kannada"),
    (0x0D00, 0x0D7F, "Malayalam"), (0x0D80, 0x0DFF, "Sinhala"),
    (0x0E00, 0x0E7F, "Thai"), (0x0E80, 0x0EFF, "Lao"),
    (0x0F00, 0x0FFF, "Tibetan"), (0x1000, 0x109F, "Myanmar"),
    (0x10A0, 0x10FF, "Georgian"), (0x1100, 0x11FF, "EastAsian"),
    (0x1200, 0x139F, "Ethiopic"), (0x13A0, 0x13FF, "Cherokee"),
    (0x1400, 0x167F, "Canadian"), (0x1780, 0x17FF, "Khmer"),
    (0x1800, 0x18AF, "Mongolian"), (0x1AB0, 0x1AFF, None),
    (0x1C80, 0x1C8F, "Cyrillic"), (0x1C90, 0x1CBF, "Georgian"),
    (0x1D00, 0x1DBF, "Latin"), (0x1DC0, 0x1DFF, None),
    (0x1E00, 0x1EFF, "Latin"), (0x1F00, 0x1FFF, "Greek"),
    (0x20D0, 0x20FF, None), (0x2C60, 0x2C7F, "Latin"),
    (0x2D00, 0x2D2F, "Georgian"), (0x2DE0, 0x2DFF, "Cyrillic"),
    (0x2E80, 0x2FDF, "EastAsian"), (0x3000, 0x9FFF, "EastAsian"),
    (0xA640, 0xA69F, "Cyrillic"), (0xA720, 0xA7FF, "Latin"),
    (0xA960, 0xA97F, "EastAsian"), (0xAB30, 0xAB6F, "Latin"),
    (0xAC00, 0xD7FF, "EastAsian"), (0xF900, 0xFAFF, "EastAsian"),
    (0xFB00, 0xFB06, "Latin"), (0xFB13, 0xFB17, "Armenian"),
    (0xFB1D, 0xFB4F, "Hebrew"), (0xFB50, 0xFDFF, "Arabic"),
    (0xFE00, 0xFE0F, None), (0xFE20, 0xFE2F, None),
    (0xFE70, 0xFEFE, "Arabic"), (0xFF21, 0xFF5A, "Latin"),
    (0xFF66, 0xFFDC, "EastAsian"), (0x20000, 0x3FFFF, "EastAsian"),
    (0xE0100, 0xE01EF, None))
_RARE = ((0x0180, 0x01CC), (0x01DD, 0x01F3), (0x01F6, 0x0217),
         (0x021C, 0x024F), (0x0250, 0x02FF), (0x0700, 0x08FF),
         (0x1100, 0x11FF), (0x3400, 0x4DBF), (0xA000, 0xA4CF),
         (0x20000, 0x3FFFF))
# Latin Extended-B and IPA letters languages write (Vietnamese, Pan-
# African alphabets, Azerbaijani's schwa, the modifier apostrophe).
_NOT_RARE = frozenset(
    "\u0186\u0189\u018a\u018e\u018f\u0190\u0194\u0196\u0197\u019d\u01a0"
    "\u01a1\u01af\u01b0\u01b7\u0254\u0256\u0257\u0259\u025b\u0263\u0268"
    "\u0272\u028b\u0292\u02bc")
# Written after a word in correct text: a note number, a registered or
# trade mark, a degree sign, primes.
_WORD_END = frozenset("\u00b9\u00b2\u00b3\u2070\u2071\u2074\u2075\u2076"
                      "\u2077\u2078\u2079\u00ae\u2122\u00b0\u2032\u2033")
# Join two parts of one word.
_JOINERS = frozenset("'\u2019\u2010\u2011-\u00b7\u2013\u2014")
_JOINING_FORMAT = frozenset("\u00ad\u200c\u200d\u2060")
_FORMAT_OK = frozenset("\u00ad\u200b\u200c\u200d\u200e\u200f\u2060\ufeff")
_VARIATION = ((0xFE00, 0xFE0F), (0x20D0, 0x20FF), (0xE0100, 0xE01EF))
_SCRIPT_STARTS = [r[0] for r in _SCRIPTS]

_INFO: Dict[str, Tuple] = {}


def _info(ch: str) -> Tuple:
    """(category, script, rare, letter, lower, upper, space) of `ch`."""
    got = _INFO.get(ch)
    if got is None:
        cp = ord(ch)
        if cp < 0x80:
            script = "Latin" if ch.isalpha() else None
        else:
            i = bisect.bisect_right(_SCRIPT_STARTS, cp) - 1
            if i >= 0 and _SCRIPTS[i][0] <= cp <= _SCRIPTS[i][1]:
                script = _SCRIPTS[i][2]
            else:
                script = "block%x" % (cp >> 7)
        rare = ch not in _NOT_RARE and any(a <= cp <= b for a, b in _RARE)
        got = (unicodedata.category(ch), script, rare, ch.isalpha(),
               ch.islower(), ch.isupper(), ch.isspace())
        if len(_INFO) < 200000:
            _INFO[ch] = got
    return got


def _own_script(ch: str, info: Tuple) -> Optional[str]:
    """The script a mark, digit or punctuation sign belongs to, when it
    belongs to one (an Armenian apostrophe, an N'Ko digit)."""
    cp = ord(ch)
    script = info[1]
    if cp < 0x0370 or cp >= 0x2000 or script in (None, "Latin") or \
            script.startswith("block"):
        return None
    return script


def oddness(left: str, mid: str, right: str,
            reading: bool = False) -> Optional[int]:
    """How odd `mid` looks between `left` and `right` (one character each,
    or empty). For a reading back, None when it cannot stand there."""
    seq = ([left] if left else []) + list(mid) + ([right] if right else [])
    info = [_info(c) for c in seq]
    first = 1 if left else 0
    last = first + len(mid)
    n = len(seq)
    score = 0
    for i in range(first, last):
        c = seq[i]
        cat, script, rare, letter, _, _, _ = info[i]
        pl = i > 0 and info[i - 1][3]
        nl = i + 1 < n and info[i + 1][3]
        kind = cat[0]
        if rare:
            score += 1
        if kind == "L":
            continue
        if kind == "C":
            if c in _JOINING_FORMAT and pl and nl:
                continue
            if c not in _FORMAT_OK:
                if reading:
                    return None
                score += 2
                continue
            score += 1
            continue
        if kind == "M":
            cp = ord(c)
            if any(a <= cp <= b for a, b in _VARIATION) and i > 0 and \
                    not info[i - 1][6]:
                continue
            j = i - 1
            while j >= 0 and info[j][0][0] == "M":
                j -= 1
            base = info[j][1] if j >= 0 and info[j][3] else False
            if base is False:
                fits = False
            elif script is None:
                fits = base in ("Latin", "Greek", "Cyrillic")
            else:
                fits = base == script
            if not fits:
                if reading:
                    return None
                score += 2
            continue
        own = _own_script(c, info[i])
        if own is not None:
            near = [info[k][1] for k in (i - 1, i + 1)
                    if 0 <= k < n and info[k][3]]
            if near and own not in near:
                if reading:
                    return None
                score += 2
                continue
        if kind == "S" or cat == "No":
            if c in _WORD_END and pl and not nl:
                continue
            if pl and nl:
                score += 2
            elif pl or nl:
                score += 1
            elif 0 < i < n - 1 and not info[i - 1][6] and \
                    not info[i + 1][6]:
                score += 1
        elif kind == "P" and pl and nl and c not in _JOINERS:
            score += 1 if c == "\u2026" else 2
    flips = 0
    for i in range(max(first - 1, 0), min(last, n - 1)):
        a, b = info[i], info[i + 1]
        if a[3] != b[3] and not (a[6] or b[6]):
            flips += 1
        if not (a[3] and b[3]):
            if (a[3] and i + 2 < n and info[i + 2][3] and
                    seq[i + 1] in _JOINERS and a[1] is not None and
                    info[i + 2][1] is not None and a[1] != info[i + 2][1]):
                score += 2
            continue
        if a[4] and b[5]:
            score += 2
        if seq[i] == "\u00c3" and ord(seq[i + 1]) >= 0x80:
            score += 1
        if a[1] is not None and b[1] is not None and a[1] != b[1]:
            if {a[1], b[1]} == {"Latin", "EastAsian"}:
                score += 1
            elif reading:
                return None
            else:
                score += 2
    return score + max(0, flips - 2)


def _a_sign(name: str, left: str, run: str, right: str) -> bool:
    try:
        back = run.encode(name).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    read_back = oddness(left, back, right, reading=True)
    if read_back is None:
        return False
    as_written = oddness(left, run, right)
    if name == "gbk":
        if len(back) >= 3 and read_back == 0 and \
                {_info(c)[1] for c in back if _info(c)[3]} in (
                    {"Cyrillic"}, {"Greek"}, {"Hebrew"}, {"Arabic"},
                    {"Armenian"}):
            return True
        return read_back + 2 <= as_written
    return read_back < as_written


def _runs(text: str) -> Iterator[Tuple[int, int, str]]:
    """Each run that reads back better through another set, as (start,
    end, the set's name), set by set in the order above; a place one set
    has claimed is not weighed again."""
    seen = set()
    weighed: Dict[Tuple[str, str, str, str], bool] = {}
    length = len(text)
    for name, run_of in _UNITS:
        for match in run_of.finditer(text):
            start, end = match.span()
            if start in seen:
                continue
            key = (name, text[start - 1] if start else "", match.group(),
                   text[end] if end < length else "")
            sign = weighed.get(key)
            if sign is None:
                sign = _a_sign(name, *key[1:])
                if len(weighed) < 100000:
                    weighed[key] = sign
            if sign:
                seen.add(start)
                yield start, end, name


def garbled(text: str, enough: int = 10) -> int:
    """The signs of letters that came out wrong in `text`: each C1
    control and replacement character, and each run that reads back
    better through another set; counting stops at `enough`."""
    found = len(_C1_OR_REPLACEMENT.findall(text))
    if found >= enough or text.isascii():
        return found
    for _place in _runs(text):
        found += 1
        if found >= enough:
            return found
    return found


# The sets in the researcher's words, for the preview's warning.
SET_NAMES = {
    "cp1252": "Windows Western", "cp1250": "Windows Central European",
    "cp1251": "Windows Cyrillic", "cp1253": "Windows Greek",
    "cp1254": "Windows Turkish", "cp1255": "Windows Hebrew",
    "cp1256": "Windows Arabic", "cp1257": "Windows Baltic",
    "cp1258": "Windows Vietnamese", "mac_roman": "the Mac's own Western set",
    "mac_latin2": "the Mac's Central European set",
    "mac_cyrillic": "the Mac's Cyrillic set",
    "mac_greek": "the Mac's Greek set",
    "mac_iceland": "the Mac's Icelandic set", "cp437": "DOS (437)",
    "cp850": "DOS Western (850)", "cp852": "DOS Central European (852)",
    "cp866": "DOS Cyrillic (866)", "koi8_r": "KOI8-R", "koi8_u": "KOI8-U",
    "shift_jis": "Shift JIS (Japanese Windows)",
    "gbk": "GBK (Chinese Windows)",
}
# A control character or the replacement character: no set to name.
LOST = None
MAX_PLACES = 1000


class Place(NamedTuple):
    start: int
    end: int
    set_name: Optional[str]     # a key of SET_NAMES, or LOST
    reads_as: str               # what it reads back as ("" when LOST)


def places(text: str, limit: int = MAX_PLACES) -> List[Place]:
    """Where `text` holds the signs `garbled` counts, in the order they
    stand, at most `limit` of them: each run with the set it reads back
    through and what it reads back as, and each control or replacement
    character."""
    found: List[Place] = []
    for match in _C1_OR_REPLACEMENT.finditer(text):
        if len(found) >= limit:
            break
        found.append(Place(match.start(), match.end(), LOST, ""))
    if not text.isascii():
        for start, end, name in _runs(text):
            if len(found) >= 2 * limit:
                break
            back = text[start:end].encode(name).decode("utf-8")
            found.append(Place(start, end, name, back))
    found.sort()
    return found[:limit]
