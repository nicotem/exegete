# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3: the hold for letters that came out wrong, as the second gates
found it, fixed.

Pinned here:

- correct text is let through, in every format: an accented word cut off
  by a long dash inside quotation marks, as a transcript marks an
  interruption ("José", the dash, the closing mark), a quoted accented
  word before a dash, French spacing before a dash, a brand's
  registered mark, Czech and Slovak capitals, a Swedish place name
  before a dash, an ellipsis before a Spanish question;
- a UTF-8 file once opened in another common set and saved again is
  held back, whichever set: Windows' Central European and Cyrillic, the
  Mac's own Western set, DOS's, KOI8, and the Latin letters GBK and
  Shift JIS leave, as well as Windows Western;
- the reading back stays cheap on a hostile file.
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import import_fixtures  # noqa: E402
import exegete.server as server  # noqa: E402
from exegete import doc_readers, import_paths, import_words  # noqa: E402

OPTIONAL = import_fixtures.optional_part_installed()
D = "\u2014"    # the long dash
NB = "\u00a0"   # the no-break space


@pytest.fixture(autouse=True)
def _scratch_is_not_hidden(tmp_path, monkeypatch):
    """pytest's scratch folders lie under AppData on Windows, which the
    system marks hidden; the rule is for the researcher's places."""
    import os
    excused = {os.path.normcase(str(p)) for p in tmp_path.parents}
    real = import_paths.hidden_step

    def hidden_step(step, info):
        if os.path.normcase(str(step)) in excused:
            return False
        return real(step, info)
    monkeypatch.setattr(import_paths, "hidden_step", hidden_step)


@pytest.fixture
def project(setup_server, qualcoder_db_path):
    return Path(qualcoder_db_path)


@pytest.fixture
def folder(tmp_path):
    place = tmp_path / "Interviews"
    place.mkdir()
    return place


def _call(**kwargs):
    return json.loads(server.import_documents(**kwargs))


def _stored(project):
    con = sqlite3.connect(str(project / "data.qda"))
    try:
        return dict(con.execute(
            "SELECT name, fulltext FROM source WHERE mediapath LIKE "
            "'/docs/%' ORDER BY id").fetchall())
    finally:
        con.close()


def _names_list(project, pairs):
    (project / "pseudonyms.json").write_text(json.dumps(
        [{"original": o, "pseudonym": p} for o, p in pairs],
        ensure_ascii=False), encoding="utf-8")


def _said(answer) -> str:
    return json.dumps(answer, ensure_ascii=False)


def _word(lines) -> bytes:
    body = "".join("<w:p>" + import_fixtures._r(
        line.replace("&", "&amp;").replace("<", "&lt;")) + "</w:p>"
        for line in lines)
    return import_fixtures.word(body)


def _odt(lines) -> bytes:
    body = "".join("<text:p>" + line.replace("&", "&amp;").replace(
        "<", "&lt;") + "</text:p>" for line in lines)
    return import_fixtures.odt(import_fixtures._content(body))


def _rtf(lines) -> bytes:
    def escaped(line):
        out = []
        for ch in line:
            if ord(ch) < 0x80:
                out.append(ch)
            else:
                try:
                    out.append("\\'%02x" % ch.encode("cp1252")[0])
                except UnicodeEncodeError:
                    out.append("\\u%d?" % ord(ch))
        return "".join(out)
    return ("{\\rtf1\\ansi\\ansicpg1252\\deff0 " + "\\par ".join(
        escaped(line) for line in lines) + "\\par}").encode("ascii")


def _page(lines) -> bytes:
    return ("<html><head><meta charset=\"utf-8\"><title>Talk</title>"
            "</head><body>" + "".join("<p>" + line + "</p>"
                                      for line in lines)
            + "</body></html>").encode("utf-8")


def _epub(lines) -> bytes:
    return import_fixtures.epub({"ch1.xhtml": import_fixtures._chapter(
        "".join("<p>" + line + "</p>" for line in lines))}, ["ch1"])


# ---------------------------------------------------------------------------
# Correct text, let through
# ---------------------------------------------------------------------------

# The QA gate's eleven forms (each came in at round 1 and was held at
# round 2), the parity gate's interrupted line, the fidelity gate's three.
QA_FORMS = [
    "P1: \u201cI was going to call Jos\u00e9" + D + "\u201d",
    "P2: \u201cS\u00ed" + D + "\u201d",
    "He said \u201cJos\u00e9\u201d" + D + "that was all.",
    "Il est arriv\u00e9" + NB + D + " enfin.",
    "Nestl\u00e9\u00ae\u2019s products.",
    "P3: \u201cPerch\u00e9" + D + "\u201d",
    "P1: \u201cAndr\u00e9" + D + D + "no, wait.\u201d",
    "SK\u00da\u0160KA",
    "\u00da\u017dASN\u00dd",
    "Platnos\u0165 SK\u00da\u0160OBN\u00ddCH programov",
    "MALM\u00d6" + D + "LUND",
]
INTERRUPTED = ("P1: She looked at me and said, \u201cJos\u00e9" + D
               + "\u201d and then stopped.")
FIDELITY_FORMS = [
    "My neighbour called out, \u201cWait, Jos\u00e9" + D
    + "\u201d and then the chair cut him off.",
    "P1: no s\u00e9\u2026\u00bfsabes?",
    "C'\u00e9tait un peu compliqu\u00e9" + NB + D + " enfin.",
]
# More correct forms the gates listed, read by the sign alone.
MORE_CORRECT = [
    "P1: \u2018At the caf\u00e9" + D + "\u2019 she said.",
    "\u201cthe caf\u00e9\u201d" + D + "she paused",
    "Chlo\u00e9" + D + D + "no",
    "Mam\u00e1" + D + "\u201cven aqu\u00ed\u201d",
    "Jos\u00e9" + D + "\u00bfvienes?",
    "all\u00e9" + D + "\u00ab non \u00bb",
    "P\u00c5" + D + "NEJ",
    "PER\u00da" + D + "UNA",
    "No s\u00e9" + D + "\u00bfme entiendes?" + D + ", era dif\u00edcil.",
    "Estaba all\u00ed" + D + "\u00a1qu\u00e9 susto!" + D
    + "cuando lleg\u00f3.",
    "\u00abNo lo s\u00e9\u00bb" + D + "dijo ella" + D + ".",
    "Pues no s\u00e9\u2026" + D + "se qued\u00f3 callada.",
    "They said \u2018ol\u00e9\u2019" + D + "and laughed.",
    "Mi ha detto \u00abperch\u00e9\u00bb" + D + "e basta.",
    "A IRM\u00c3" + D + "ela n\u00e3o veio.",
    "\u00bfQU\u00c9 PAS\u00d3" + D + "EN SERIO?",
    "\u0158ekla: \u201eBylo to t\u011b\u017ek\u00e9\u201c" + D
    + "a ode\u0161la.",
    "MALM\u00d6\u00b2 och LUND\u00b3.",
    "Ella dijo que s\u00ed" + D + "\u00abya veremos\u00bb.",
    "Il est all\u00e9 jusqu'\u00e0" + D + NB + "enfin, presque.",
    "Intensit\u00e9" + NB + "\u2022 Risque de pluie",
    "Les salari\u00e9\u00b7e\u00b7s et les \u00e9tudiant\u00b7e\u00b7s.",
    "P1: N\u00c3O" + D + "N\u00c3O!",
    "\u00c5STR\u00d6M\u00b2 said",
    "Ela disse \u00abIRM\u00c3\u00bb em voz alta.",
    # Persian's zero-width non-joiner, Ukrainian's apostrophe letter,
    # Slovak's no-break space after a one-letter word, a range.
    "\u062c\u0645\u0639\u200c\u0622\u0648\u0631\u06cc",
    "\u0422\u0435\u043c\u0430 \u00ab\u041c\u02bc\u044f\u043a\u0456\u0441"
    "\u0442\u044c\u00bb",
    "Naozaj chcete odstr\u00e1ni\u0165 pole s\u00a0\u00fadajmi?",
    "\u042f\u2014\u0410",
    # Chinese and Japanese written against Latin words.
    "\u6b63\u5728\u4e0eiCloud\u540c\u6b65\u2026",
    "FaceTime\u901a\u8bdd",
    # Words run together with a capital inside, an alphabet, a range, as
    # interface strings write them (Word's and macOS's own).
    "\u041a\u043e\u043c\u0430\u043d\u0434\u0430\u041f\u043e\u0441"
    "\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0439\u041e\u0431"
    "\u0440\u0430\u0431\u043e\u0442\u043a\u0438\u0412\u0445\u043e"
    "\u0434\u043d\u044b\u0445\u041e\u0431\u044a\u0435\u043a\u0442"
    "\u043e\u0432ArtO",
    "AUTOTEXT \u042d\u043b\u0435\u043c\u0435\u043d\u0442\u0410"
    "\u0432\u0442\u043e\u0442\u0435\u043a\u0441\u0442\u0430",
    "\u0410\u0430\u0411\u0431\u0412\u0432\u0413\u0433\u0414\u0434",
    "\u0438\u0417&\u041c\u0415\u041d\u0418\u0422\u042c",
    "\u0130leriGe\u00e7mi\u015f\u00d6\u011fesi",
    "Olu\u015fturSe\u00e7imdenSayfaNumaras\u0131\u00dcst",
    "Ak\u0131\u015f\u00e7izelgesi\u0130\u00e7Depolama",
    "\u03ce\u03ae\u03b7\u03a5\u03a9",
    "&Alfabetisk \u00c5\u2013A",
    "\u043d\u0430\u0432\u0447\u0430\u043d\u043d\u044f;;\u043c"
    "\u02bc\u044f\u043a\u0430",
    # Word's Hungarian alphabet: read back through Windows Western, its
    # "\u00c1b" would be a control character.
    "aA\u00e1\u00c1bBcCdDeE\u00e9\u00c9fFgGhHiI\u00ed\u00cdjJkKlLmMnNoO"
    "\u00f3\u00d3\u00f6\u00d6\u0151\u0150pPqQrRsStTuU\u00fa\u00da"
    "\u0171\u0170vVzZ.",
    # A trade mark after a capital; a Chinese question and a Russian
    # interface name that read back as a mark or punctuation of another
    # script.
    "NESCAF\u00c9\u2122 and CAF\u00c9\u00ae were on the menu.",
    "\u8981\u505c\u6b62\u9304\u97f3\u55ce\uff1f",
    "\u041f\u0435\u0440\u0435\u0439\u0442\u0438\u041a\u0423\u0440"
    "\u043e\u0432\u043d\u044e\u041e\u0431\u044a\u0435\u043a\u0442"
    "\u0430",
]


def test_the_sign_lets_correct_text_through():
    for line in QA_FORMS + [INTERRUPTED] + FIDELITY_FORMS + MORE_CORRECT:
        assert doc_readers.garbled(line) == 0, line


FORMATS = {
    ".txt": lambda lines: "\n".join(lines).encode("utf-8"),
    ".md": lambda lines: "\n\n".join(lines).encode("utf-8"),
    ".html": _page,
    ".docx": _word,
    ".odt": _odt,
    ".rtf": _rtf,
}
if OPTIONAL:
    FORMATS[".epub"] = _epub


def _all_ready(project, folder, files):
    for name, data in files.items():
        (folder / name).write_bytes(data)
    preview = _call(paths=[str(folder)])
    assert preview.get("held_back", []) == [], preview
    done = _call(paths=[str(folder)], preview_token=preview["preview_token"])
    assert done["success"] is True, done
    return _stored(project)


def test_the_qa_gates_eleven_forms_come_in_as_text_and_as_word(project,
                                                                 folder):
    stored = _all_ready(project, folder, {
        "forms.txt": FORMATS[".txt"](QA_FORMS),
        "forms.docx": _word(QA_FORMS)})
    assert len(stored) == 2
    for text in stored.values():
        for line in QA_FORMS:
            assert line in text, line


@pytest.mark.parametrize("suffix", sorted(FORMATS))
def test_an_interrupted_line_comes_in_in_every_format(project, folder,
                                                       suffix):
    """The parity gate's transcript line, held at round 2 in every
    format but PDF; QualCoder 4.0 imports it with the right letters."""
    _names_list(project, [("Maria Brown", "Participant A")])
    lines = ["Interviewer: What did she say?", INTERRUPTED,
             "P1: \u2018At the caf\u00e9" + D + "\u2019 she said."]
    (stored,) = _all_ready(project, folder, {
        "talk" + suffix: FORMATS[suffix](lines)}).values()
    assert "\u201cJos\u00e9" + D + "\u201d and then stopped." in stored


def test_the_fidelity_gates_three_files_come_in(project, folder):
    stored = _all_ready(project, folder, {
        "interview_23_english.docx": _word(FIDELITY_FORMS[:1]),
        "entrevista_03.txt": FIDELITY_FORMS[1].encode("utf-8"),
        "entretien_05.docx": _word(FIDELITY_FORMS[2:])})
    assert len(stored) == 3


# ---------------------------------------------------------------------------
# Garbled through other sets, held back
# ---------------------------------------------------------------------------

def _once(text: str, read_as: str) -> str:
    """`text` saved as UTF-8, opened once as `read_as` (every byte
    defined) and saved again as UTF-8."""
    return text.encode("utf-8").decode(read_as)


CZECH = "Tazatel: Kdo v\u00e1s vozil?\nP1: Vozil m\u011b soused " \
    "Ji\u0159\u00ed " \
    "Dvo\u0159\u00e1k, obvykle s man\u017eelkou.\n"
UKRAINIAN = ("\u0406\u043d\u0442\u0435\u0440\u0432'\u044e\u0435\u0440: "
             "\u0425\u0442\u043e \u0432\u0430\u0441 \u0432\u043e\u0437\u0438"
             "\u0432?\nP1: \u041c\u0435\u043d\u0435 \u0432\u043e\u0437\u0438"
             "\u0432 \u0441\u0443\u0441\u0456\u0434 \u041f\u0435\u0442\u0440"
             "\u043e \u0428\u0435\u0432\u0447\u0435\u043d\u043a\u043e.\n")
FRENCH = ("Intervieweur : Qui vous conduisait ?\nP1 : C'\u00e9tait ma "
          "voisine Agn\u00e8s Dupr\u00e9, d\u2019habitude.\n")
POLISH = ("Interviewer: Kto pana wozi\u0142?\nP1: Zawozi\u0142 mnie "
          "s\u0105siad J\u00f3zef Wo\u017aniak, zwykle z \u017con\u0105.\n")
LISTED = [("Ji\u0159\u00ed", "Participant A"),
          ("Dvo\u0159\u00e1k", "Participant B"),
          ("\u041f\u0435\u0442\u0440\u043e", "Participant C"),
          ("Agn\u00e8s Dupr\u00e9", "Participant D"),
          ("J\u00f3zef", "Participant E"),
          ("Wo\u017aniak", "Participant F")]


def test_the_security_gates_eight_files_are_held_back(project, folder):
    """Each came in at round 2 as "1 file ready.", every listed name in it
    unreplaced."""
    srt = "1\n00:00:01,000 --> 00:00:02,000\n"
    files = {
        "czech_cp1250.txt": _once(CZECH, "cp1250"),
        "ukrainian_cp1251.txt": _once(UKRAINIAN, "cp1251"),
        "french_mac.txt": _once(FRENCH, "mac_roman"),
        "french_mac.html": "<p>" + _once(FRENCH, "mac_roman") + "</p>",
        "french_mac.srt": srt + _once(FRENCH, "mac_roman"),
        "polish_mac.md": _once(POLISH, "mac_roman"),
        "czech_cp850.txt": _once(CZECH, "cp850"),
    }
    _names_list(project, LISTED)
    for name, text in files.items():
        (folder / name).write_bytes(text.encode("utf-8"))
    (folder / "french_mac.docx").write_bytes(
        _word(_once(FRENCH, "mac_roman").splitlines()))
    preview = _call(paths=[str(folder)])
    assert preview["summary"] == "0 files ready; 8 held back.", preview
    for held in preview["held_back"]:
        # the warning, with what was seen; the way through on the
        # researcher's word (ruling 63)
        assert held["reason"].startswith(
            import_words.HELD_BACK["garbled_fixed"].split("{")[0])
        assert "import_files_with_garbled_letters" in held["reason"]
    said = _said(preview)
    for original, _ in LISTED:
        assert original not in said
    assert _stored(project) == {}


# Each interview text through every set that defines the bytes it needs:
# the security gate's sweep.
TWELVE = {
    "russian": "\u0418\u043d\u0442\u0435\u0440\u0432\u044c\u044e\u0435\u0440"
               ": \u041a\u0442\u043e \u0432\u0430\u0441 \u0432\u043e\u0437"
               "\u0438\u043b?\nP1: \u041c\u0435\u043d\u044f \u0432\u043e\u0437"
               "\u0438\u043b \u0441\u043e\u0441\u0435\u0434 \u041f\u0451\u0442"
               "\u0440 \u0421\u043c\u0438\u0440\u043d\u043e\u0432.\n",
    "ukrainian": UKRAINIAN,
    "polish": POLISH,
    "czech": CZECH,
    "greek": "\u03a3\u03c5\u03bd\u03b5\u03bd\u03c4\u03b5\u03c5\u03ba\u03c4"
             "\u03ae\u03c2: \u03a0\u03bf\u03b9\u03bf\u03c2;\nP1: \u039f "
             "\u03b3\u03b5\u03af\u03c4\u03bf\u03bd\u03b1\u03c2 \u0393\u03b9"
             "\u03ac\u03bd\u03bd\u03b7\u03c2.\n",
    "french": FRENCH,
    "english": "Interviewer: Who drove you?\nP1: It\u2019s Maria Brown "
               "\u2013 she\u2019d drive me.\n",
    "turkish": "G\u00f6r\u00fc\u015fmeci: Sizi kim g\u00f6t\u00fcrd\u00fc?\n"
               "P1: Kom\u015fum Ay\u015fe Y\u0131lmaz "
               "g\u00f6t\u00fcrd\u00fc.\n",
    "japanese": "\u30a4\u30f3\u30bf\u30d3\u30e5\u30a2\u30fc\uff1a\u8ab0\u304c"
                "\u9001\u3063\u3066\u304f\u308c\u307e\u3057\u305f\u304b\uff1f"
                "\nP1\uff1a\u96a3\u306e\u7530\u4e2d\u3055\u3093\u3067\u3059"
                "\u3002\n",
    "chinese": "\u91c7\u8bbf\u8005\uff1a\u8c01\u9001\u4f60\u53bb\u7684\uff1f"
               "\nP1\uff1a\u6211\u7684\u90bb\u5c45\u738b\u4f1f\u9001\u6211"
               "\u53bb\u7684\u3002\n",
    "hebrew": "\u05de\u05e8\u05d0\u05d9\u05d9\u05df: \u05de\u05d9 \u05d4\u05e1"
              "\u05d9\u05e2 \u05d0\u05d5\u05ea\u05da?\nP1: \u05d4\u05e9\u05db"
              "\u05df \u05e9\u05dc\u05d9 \u05d3\u05d5\u05d3 \u05db"
              "\u05d4\u05df."
              "\n",
    "arabic": "\u0627\u0644\u0645\u062d\u0627\u0648\u0631: \u0645\u0646 \u0623"
              "\u0648\u0635\u0644\u0643\u061f\nP1: \u062c\u0627\u0631\u064a "
              "\u0623\u062d\u0645\u062f \u062d\u0633\u0646.\n",
}
SETS = ["latin-1", "cp1252", "cp1250", "cp1251", "cp1253", "cp1254",
        "cp1255", "cp1256", "cp1257", "mac_roman", "mac_cyrillic",
        "mac_latin2", "mac_greek", "mac_turkish", "mac_iceland", "cp1258",
        "cp437", "cp850", "cp852", "cp866", "koi8-r", "koi8-u", "iso8859-2",
        "iso8859-5", "iso8859-7", "gbk", "shift_jis"]


@pytest.mark.parametrize("read_as", SETS)
def test_every_script_through_every_set(read_as):
    tried = 0
    for name, text in TWELVE.items():
        try:
            once = _once(text, read_as)
        except UnicodeDecodeError:
            continue
        if once != text:
            tried += 1
            assert doc_readers.garbled(once) > 0, (name, once)
    assert tried
    for name, text in TWELVE.items():
        assert doc_readers.garbled(text) == 0, name


# A text only that set reads back (the others read back none of it, or
# its twin's characters differ), and a text only that rule catches.
ONLY = {
    "cp1252": ("\u041f\u0430\u043f\u0430 \u0434\u0430\u0432\u0430\u043b.",
               "cp1252"),
    "cp1254": ("\u041f\u0430\u043f\u0430 \u0434\u0430\u0432\u0430\u043b.",
               "cp1254"),
    "cp1258": ("Herr M\u00fcller kam.", "cp1258"),
    # macOS's own strings, read once through the set
    "mac_roman": ("Apple Podcasts \u092c\u094d\u0930\u093e\u0909\u091c"
                  "\u093c \u0915\u0930\u0947\u0902", "mac_roman"),
    "mac_iceland": ("Compatibilit\u00e0 limitata", "mac_iceland"),
    "koi8_r": ("Maak netwerk aan\u2026", "koi8_r"),
    "koi8_u": ("Maak netwerk aan\u2026", "koi8_u"),
    # letters and other characters alternating: macOS's Japanese "off"
    "alternation": ("Wi-Fi: \u30aa\u30d5", "mac_roman"),
    # a symbol between a digit and a letter: a no-break space
    "symbols": ("Darrers 5\u00a0anys", "mac_roman"),
    # two scripts either side of a dash
    "a dash between scripts": ("Fahrpreise mit \u00d6PNV-Karte", "cp1251"),
    # "\u00c3" before a letter other than A to Z: "\u00caTRE" in capitals
    "A tilde": ("\u00caTRE", "cp1252"),
}


@pytest.mark.parametrize("which", sorted(ONLY))
def test_each_set_and_rule_has_a_text_only_it_reads(which):
    text, read_as = ONLY[which]
    assert doc_readers.garbled(text) == 0
    assert doc_readers.garbled(_once(text, read_as)) > 0, _once(text,
                                                                read_as)


def test_the_same_run_between_the_same_neighbours_is_weighed_once(
        monkeypatch):
    from exegete import garbled_text
    calls = []
    real = garbled_text._a_sign

    def counted(*args):
        calls.append(args)
        return real(*args)
    monkeypatch.setattr(garbled_text, "_a_sign", counted)
    assert doc_readers.garbled("Jos" + ("\u00e9" + D + "\u201d") * 3000) > 0
    assert 0 < len(calls) < 20, len(calls)


def test_a_long_garbled_run():
    """A paragraph of Chinese with no space, garbled through Windows
    Western, is one run of hundreds of characters, and a sign."""
    paragraph = ("\u6211\u7684\u90bb\u5c45\u738b\u4f1f\u9001\u6211\u53bb"
                 "\u7684\uff0c") * 12
    once = paragraph.encode("utf-8").decode("cp1252", "ignore")
    assert len(once) > 200
    assert doc_readers.garbled("P1: " + once + "\n") > 0


def test_an_emoji_with_its_variation_selector_read_back():
    """A heart written with the selector that asks for its colour form,
    garbled through the Mac's own set, alone in its text."""
    once = _once("P1: Thanks \u2764\ufe0f\n", "mac_roman")
    assert doc_readers.garbled(once) > 0


def _ordinary(length: int) -> str:
    line = ("Il \u00e9tait une fois un caf\u00e9 \u00e0 Paris, o\u00f9 "
            "Jos\u00e9 prenait le th\u00e9. ")
    return (line * (length // len(line) + 1))[:length]


@pytest.fixture
def untraced():
    """tests/test_scale_media.py leaves tracemalloc tracing on for the rest
    of a full run, which makes every allocation cost about ten times
    more; these tests time the reading as it runs outside the suite."""
    import tracemalloc
    tracing = tracemalloc.is_tracing()
    if tracing:
        tracemalloc.stop()
    yield
    if tracing:
        tracemalloc.start()


def _cheap(hostile: str) -> None:
    ordinary = _ordinary(len(hostile))
    start = time.perf_counter()
    assert doc_readers.garbled(ordinary) == 0
    usual = time.perf_counter() - start
    start = time.perf_counter()
    doc_readers.garbled(hostile)
    spent = time.perf_counter() - start
    assert spent < 10 * usual + 0.5, (spent, usual)


def test_a_hostile_file_costs_about_an_ordinary_one(untraced):
    """Runs shaped like UTF-8 that are no sign (accented words before
    dashes and quotation marks, in some five thousand forms, a million
    characters) cost about what ordinary text of the same size costs:
    each run between the same neighbours is weighed once."""
    leads = [chr(c) for c in range(0xE0, 0xF0)]
    tails = [D + "\u201d", "\u201d" + D, NB + D, D + D, "\u2026\u00bf",
             D + "\u00ab"]
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    hostile = "".join(
        letters[i % 52] + leads[(i // 52) % 16] + tails[(i // 832) % 6]
        + " " for i in range(200000))[:1000000]
    assert doc_readers.garbled(hostile[:30000]) == 0
    _cheap(hostile)


def test_one_long_run_costs_about_an_ordinary_one(untraced):
    """A million characters shaped like UTF-8 in one run, and read back
    through another set as many small ones, each weighed once."""
    _cheap("Jos" + ("\u00e9" + D + "\u201d") * 333000)
