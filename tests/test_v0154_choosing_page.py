# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.4, choosing occurrences, second part: the page.

The page for choosing occurrences labels each occurrence with its number
in bold, as the preview numbers its rows, before its id, and a tick box
before the number. At its foot a bar gives the line to copy for the
occurrences ticked: "File 12, numbering q8x2dm: leave occurrences 3, 7,
12 as they are.", the file's id, the list's numbering and the numbers,
nothing of the text. Boxes and bar are hidden until the page's one
script shows them, so a browser that runs no script shows the numbers
alone. The page's policy allows that script by the SHA-256 of its text
and no other; the reading copy and the import page keep the policy that
allows none. The script sets every box to its written state when the
page loads, builds the line again at each tick, and copies it through
the clipboard, or selects it in its read-only field where the clipboard
is refused or absent. The block's notes say what a pasted line gives,
their example the line the script builds.

The script is run under Node (test 10), with a stub of the calls it
makes; it comes with CI's runners, where the test fails rather than
skips without it. The right-to-left tests of the page, which lay each
label out with its box and number, are v0.15.3's
(`test_v0153_occurrences_page.py`, TestRightToLeft), adapted.

The fixtures and helpers are the flagship's own
(`test_v012_pseudonymise_tool.py`) and v0.15.3's
(`test_v0153_occurrence_ids.py`, `test_v0153_occurrences_page.py`).
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import exegete.server as server  # noqa: E402
from exegete import import_page, occurrences, reading_copy  # noqa: E402
from exegete.database import QualcoderDatabase  # noqa: E402
from test_v012_pseudonymise_tool import call, preview_of  # noqa: E402
from test_v0153_occurrence_ids import block, names_list  # noqa: E402
from test_v0153_occurrences_page import (  # noqa: E402
    TOM, TOMS, fresh, labels, page_of)

# The example the notes give, and the line the script must build for it
EXAMPLE = ("File 12, numbering q8x2dm: leave occurrences 3, 7, 12 as they "
           "are.")
ONE = "File 12, numbering q8x2dm: leave occurrence 3 as it is."
# What the policy, the bar and the boxes look like on the page
POLICY_META = re.compile(
    r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">')
SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.DOTALL)
BAR = re.compile(r'<div id="pick-bar" class="pick-bar" role="region" '
                 r'aria-label="[^"]+" data-file="(\d+)" '
                 r'data-numbering="([0-9a-z]+)" hidden>(.*?)</div>',
                 re.DOTALL)


def facts_of(page):
    page = " ".join(page.split())
    return page[page.index('<ul class="facts">'):page.index("</ul>")]


class TestThePage:
    """Test 9: the labels' boxes and numbers, the bar, the script and the
    policy."""

    @pytest.mark.parametrize("path", ["typed", "names list"])
    def test_each_label_numbered_as_the_block(self, tmp_path, path):
        """Each label holds its box, carrying its number, hidden, not kept
        across a reload, with a name of its own, and its bold number: the
        block's rows, number for number and id for id, on both paths. The
        bar, hidden, carries the file's id and the block's numbering,
        which the facts give too. Red when a label has no box or number,
        or numbers from 0."""
        with fresh(tmp_path, TOMS) as folder:
            arguments = {"mapping": TOM, "choose_occurrences": True}
            if path == "names list":
                names_list(folder, TOM)
                arguments.update(mapping=None, use_project_pseudonyms=True)
            out = call(**arguments)
            assert "preview_token" in out, out
            page = page_of(folder)
            rows = block(out)["listed"]
            found = labels(page)
            assert [(number, one) for number, _box, _named, _ticked, one,
                    _left in found] == [(row["number"], row["id"])
                                        for row in rows]
            assert all(number == box == named for number, box, named, *_
                       in found)
            assert not any(ticked for _n, _b, _m, ticked, _id, _l in found)
            boxes = re.findall(r'<input type="checkbox"[^>]*>', page)
            assert len(boxes) == len(rows) == 4
            assert all(" hidden " in box and 'autocomplete="off"' in box
                       for box in boxes)
            names = re.findall(r'aria-label="([^"]+)"', "".join(boxes))
            assert len(set(names)) == len(names) == 4
            [(file_id, code, inside)] = BAR.findall(page)
            assert int(file_id) == 1
            assert code == block(out)["numbering"]
            assert code in facts_of(page)
            # The field and the button are inside the bar, hidden with it
            assert ('<textarea id="pick-line" rows="2" readonly '
                    'autocomplete="off"') in inside
            assert 'id="pick-copy"' in inside and 'role="status"' in inside

    def test_the_boxes_of_a_list_come_ticked(self, tmp_path):
        """With a list, by numbers alone, the boxes of those it leaves come
        ticked and their labels say so; the facts say they were left by
        the list the preview was given, never "of ids", which a list of
        numbers is not."""
        with fresh(tmp_path, TOMS) as folder:
            chosen = call(mapping=TOM, choose_occurrences=True)
            out = call(mapping=TOM, choose_occurrences=True,
                       leave_numbers=[2, 4],
                       numbering=block(chosen)["numbering"])
            assert "preview_token" in out, out
            page = page_of(folder)
            assert [(number, ticked, left) for number, _b, _m, ticked, _id,
                    left in labels(page)] == [
                (1, False, False), (2, True, True), (3, False, False),
                (4, True, True)]
            facts = facts_of(page)
            assert "by the list the preview was given" in facts
            assert "of ids" not in facts

    def test_one_script_by_its_digest(self, tmp_path):
        """The page holds one script element, whose text is Exegete's
        constant, and its policy is the reading copy's with that script
        allowed by the SHA-256 of the element's text, as a browser
        reckons it, and no other source. A text holding a script stays
        text. The script holds no "<", so nothing in it ends its element.
        Red when the digest is not the script's, or the policy allows any
        script."""
        text = 'Tom wrote <script>alert("x")</script> and left.\n'
        with fresh(tmp_path, text) as folder:
            preview_of(mapping=TOM, choose_occurrences=True)
            page = page_of(folder)
        [script] = SCRIPT.findall(page)
        assert script == occurrences.PICK_SCRIPT
        assert "<" not in occurrences.PICK_SCRIPT
        digest = base64.b64encode(hashlib.sha256(
            script.encode("utf-8")).digest()).decode("ascii")
        [policy] = POLICY_META.findall(page)
        assert policy == (reading_copy.POLICY
                          + f"; script-src 'sha256-{digest}'")
        assert "unsafe-inline'" not in policy.split("script-src")[1]
        assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in page

    def test_the_reading_copy_and_the_import_page_hold_none(self):
        """The reading copy and the import page keep the policy that
        allows no script, and hold none, a text holding one included."""
        text = 'He wrote <script>alert("x")</script>.'
        copy, _counts = reading_copy.build_page(
            project_name="p", file_id=1, file_name="f.txt", text=text,
            segments=[], annotations=[], file_memo=None,
            written_at=datetime(2026, 11, 10, 9, 0))
        checking = import_page.build(
            [{"label": "f.txt", "seen": "Seen.", "text": text,
              "places": []}], datetime(2026, 11, 10, 9, 0))
        for page in (copy, checking):
            assert POLICY_META.findall(page) == [reading_copy.POLICY]
            assert "script-src" not in reading_copy.POLICY
            assert "<script" not in page

    def test_without_its_script_the_page_shows_neither(self):
        """Read without its script, the page shows no box and no bar: each
        box and the bar carry `hidden`, which the page's style keeps above
        any rule that would show them; every other control is inside the
        bar. The script finds by their ids the bar and what it holds, and
        the boxes by their class. Red when a box or the bar is shown
        before the script runs."""
        page, _counts = occurrences.build_page(
            project_name="p", file_id=12, file_name="f.txt",
            text="Tom met Tom.\nAnn and Tom.", written_at=datetime(
                2026, 11, 10, 9, 0), numbering="q8x2dm",
            marks=[(0, 3, "aaaaa"), (8, 11, "bbbbb"), (21, 24, "ccccc")],
            left={1})
        assert "[hidden]{display:none!important}" in occurrences.PAGE_STYLE
        bar = page[page.index('<div id="pick-bar"'):]
        bar = bar[:bar.index("</div>")]
        assert bar.startswith('<div id="pick-bar"') and " hidden>" in bar
        outside = page.replace(bar, "")
        boxes = re.findall(r"<input\b[^>]*>", outside)
        assert len(boxes) == 3
        assert all(" hidden " in box and 'class="pick"' in box
                   for box in boxes)
        assert "<button" not in outside and "<textarea" not in outside
        assert "<textarea" in bar and "<button" in bar
        for wanted in re.findall(r'getElementById\("([^"]+)"\)',
                                 occurrences.PICK_SCRIPT):
            assert f'id="{wanted}"' in page, wanted
        assert 'querySelectorAll("input.pick")' in occurrences.PICK_SCRIPT

    def test_a_page_needs_its_numbering(self):
        """The bar carries a numbering as the block makes one, or the page
        is not built."""
        for code in (None, "", "Q8X2DM", "18x2dm", "q8x2d", "q8x2du",
                     'q8"2dm'):
            with pytest.raises(ValueError):
                occurrences.build_page(
                    project_name="p", file_id=1, file_name="f.txt",
                    text="Tom.", marks=[(0, 3, "aaaaa")], left=set(),
                    written_at=datetime(2026, 11, 10, 9, 0), numbering=code)

    def test_the_line_takes_the_place_of_any_list(self):
        """The bar says that the line takes the place of any list given
        before, so that every occurrence to leave is ticked: ticks on an
        earlier page of the same list, still open, would drop a choice
        given since. Red with the bar's words as before."""
        page, _counts = occurrences.build_page(
            project_name="p", file_id=12, file_name="f.txt",
            text="Tom met Tom.", marks=[(0, 3, "aaaaa"), (8, 11, "bbbbb")],
            left=set(), written_at=datetime(2026, 11, 11, 9, 0),
            numbering="q8x2dm")
        [(_file, _code, inside)] = BAR.findall(page)
        inside = " ".join(inside.split())
        assert "the place of any list given before" in inside
        assert "every occurrence you want left" in inside

    def test_a_second_skip_link_leads_to_the_bar(self):
        """After the skip link to the text, a second leads to the bar, so
        that a keyboard reaches the line without passing every box. It is
        hidden, with the bar, until the script shows both (test 10). Red
        without the link."""
        page, _counts = occurrences.build_page(
            project_name="p", file_id=12, file_name="f.txt",
            text="Tom met Tom.", marks=[(0, 3, "aaaaa"), (8, 11, "bbbbb")],
            left=set(), written_at=datetime(2026, 11, 11, 9, 0),
            numbering="q8x2dm")
        links = re.findall(r'<a class="skip"([^>]*)>([^<]*)</a>', page)
        assert [href for href in (re.search(r'href="([^"]+)"', attributes)
                                  .group(1) for attributes, _ in links)] \
            == ["#text", f"#{occurrences.PICK_BAR}"]
        second = links[1][0]
        assert f'id="{occurrences.PICK_SKIP}"' in second
        assert second.endswith(" hidden")
        assert page.index(f'id="{occurrences.PICK_SKIP}"') < \
            page.index("<header>")
        assert f'getElementById("{occurrences.PICK_SKIP}")' in \
            occurrences.PICK_SCRIPT


class TestTheNotes:
    """The texts that say what the page gives (the design's test 12, the
    part that names the page): the notes and the brief."""

    def test_the_notes_give_the_scripts_line(self):
        """The two notes that name the page say its bold numbers are the
        rows', and give, for an example, the line the script builds
        (`the_line`, which test 10 holds to the script): its file in
        file_id, its own numbering, every number it names. The block's
        own note, which stands where no page was written, names no page
        and no line. Red when a note's example is not the script's."""
        assert occurrences.the_line(12, "q8x2dm", [12, 3, 7, 3]) == EXAMPLE
        assert occurrences.the_line(12, "q8x2dm", [3]) == ONE
        for note in (server._OCCURRENCES_NEXT_OPENED,
                     server._OCCURRENCES_NEXT_TO_OPEN):
            assert f'"{EXAMPLE}"' in note
            for words in ("in bold", "file_id", "the line's own numbering",
                          "leave_numbers", "ask for the line"):
                assert words in note, (words, note[:60])
        own = QualcoderDatabase.PSEUDONYMISE_OCCURRENCES_NEXT
        assert "page" not in own and "q8x2dm" not in own
        assert "line it gives" not in own

    def test_the_brief_names_the_line(self):
        """The brief's privacy section names the bold numbers and the line
        the page gives, and never asks for the page's words."""
        brief = " ".join(server.BRIEF_FULL.split())
        privacy = brief[brief.index("## 11. Privacy"):brief.index("## 12. ")]
        for words in ("in bold", "paste the line the page gives them",
                      "a pasted line's own", "never ask them for words of "
                      "the text it shows"):
            assert words in privacy, words


# The harness that runs the page's script under Node: a stub of the
# calls the script makes (its own elements by id, the boxes by their
# selector, the older copy command and the clipboard), in which every
# other part of the page, the text included, throws when it is read
HARNESS = r"""
"use strict";
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[2], "utf8");
const OWN = ["pick-bar", "pick-line", "pick-copy", "pick-count",
             "pick-status", "pick-skip"];
let inClick = false;

function untouchable(what) {
  return new Proxy({}, {
    get(_target, key) { throw new Error("read " + what + " " + String(key)); },
    set(_target, key) { throw new Error("wrote " + what + " " + String(key)); },
  });
}

function element(name, log) {
  const listeners = {};
  return {
    hidden: true, disabled: false, value: "", textContent: "", dataset: {},
    addEventListener(type, handler) {
      (listeners[type] = listeners[type] || []).push(handler);
    },
    focus() { log.push(name + " focused"); },
    select() { log.push(name + " selected"); },
    fire(type) {
      (listeners[type] || []).forEach((handler) => handler({ type }));
    },
  };
}

function load(options) {
  const log = [];
  const own = {};
  OWN.forEach((id) => { own[id] = element(id, log); });
  own["pick-bar"].dataset = { file: "12", numbering: "q8x2dm" };
  const boxes = [];
  for (let n = 1; n !== options.count + 1; n += 1) {
    const box = element("box " + n, log);
    box.dataset = { n: String(n) };
    box.defaultChecked = (options.written || []).includes(n);
    const restored = (options.restored || {})[n];
    box.checked = restored === undefined ? box.defaultChecked : restored;
    boxes.push(box);
  }
  const text = untouchable("the text");
  const page = new Proxy({
    getElementById(id) { return own[id] || text; },
    querySelectorAll(selector) {
      if (selector === "input.pick") { return boxes; }
      throw new Error("asked for " + selector);
    },
    execCommand(name) {
      log.push("copy command " + name);
      return options.copyCommand === true;
    },
  }, {
    get(target, key) {
      if (key in target) { return target[key]; }
      throw new Error("read the document's " + String(key));
    },
  });
  const clipboard = {
    writeText(line) {
      log.push("clipboard " + (inClick ? "in the click" : "outside it") +
               ": " + line);
      if (options.clipboard === "throws") { throw new Error("refused"); }
      return options.clipboard === "refuses" ?
        Promise.reject(new Error("NotAllowedError")) : Promise.resolve();
    },
  };
  const navigator = options.clipboard === "none" ? {} : { clipboard };
  vm.runInContext(script, vm.createContext({ document: page, navigator }));
  return { own, boxes, log };
}

function tick(state, numbers, checked) {
  numbers.forEach((n) => {
    const box = state.boxes[n - 1];
    box.checked = checked;
    box.fire("change");
  });
}

async function click(state) {
  inClick = true;
  try { state.own["pick-copy"].fire("click"); } finally { inClick = false; }
  await new Promise((resolve) => setTimeout(resolve, 0));
}

function seen(state) {
  return {
    line: state.own["pick-line"].value,
    copy_off: state.own["pick-copy"].disabled,
    count: state.own["pick-count"].textContent,
    status: state.own["pick-status"].textContent,
    bar_hidden: state.own["pick-bar"].hidden,
    skip_hidden: state.own["pick-skip"].hidden,
    boxes_hidden: state.boxes.filter((box) => box.hidden).length,
    ticked: state.boxes.filter((box) => box.checked).map(
      (box) => Number(box.dataset.n)),
    log: state.log,
  };
}

async function main() {
  const out = {};
  let state = load({ count: 12, written: [2, 5],
                     restored: { 4: true, 5: false } });
  out.loaded = seen(state);
  state = load({ count: 12 });
  out.none = seen(state);
  tick(state, [12, 3, 7], true);
  out.three = seen(state);
  tick(state, [7, 12], false);
  out.one = seen(state);
  tick(state, [3], false);
  out.untick = seen(state);
  await click(state);
  out.click_without_a_line = seen(state);
  state = load({ count: 501 });
  const every = state.boxes.map((box) => Number(box.dataset.n));
  tick(state, every.slice(0, 500), true);
  out.most = seen(state);
  tick(state, [501], true);
  out.past = seen(state);
  for (const [name, options] of [
      ["copied", { clipboard: "works" }],
      ["refused", { clipboard: "refuses" }],
      ["throws", { clipboard: "throws" }],
      ["absent", { clipboard: "none" }],
      ["older_command", { clipboard: "none", copyCommand: true }]]) {
    state = load(Object.assign({ count: 12 }, options));
    tick(state, [3, 7, 12], true);
    await click(state);
    out[name] = seen(state);
  }
  process.stdout.write(JSON.stringify(out));
}

main().catch((error) => {
  process.stderr.write(String(error && error.stack || error));
  process.exit(1);
});
"""


def _node():
    """Node, or a skip where it is not on the path; in CI, whose runners
    carry it, a failure, so that the test is never skipped there."""
    found = shutil.which("node")
    if found is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("Node is not on CI's path: the page's script is "
                        "run under it")
        pytest.skip("Node is not on the path: the page's script is run "
                    "under it")
    return found


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    """What the page's script did under the harness, scene by scene."""
    node = _node()
    folder = tmp_path_factory.mktemp("script")
    (folder / "pick.js").write_text(occurrences.PICK_SCRIPT,
                                    encoding="utf-8")
    (folder / "harness.js").write_text(HARNESS, encoding="utf-8")
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("NODE_")}
    done = subprocess.run(
        [node, str(folder / "harness.js"), str(folder / "pick.js")],
        capture_output=True, text=True, timeout=120, cwd=str(folder),
        env=environment)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


class TestTheScript:
    """Test 10: the page's script, run under Node with a stub of the
    calls it makes."""

    def test_at_load_every_box_takes_its_written_state(self, ran):
        """A box a browser ticked against its written state, as one that
        keeps a form's state across a reload can, is set back, and so is
        one it unticked; the line is built from the written state, and
        boxes, bar and the skip link to the bar are shown. Red when the
        script keeps the state it finds, or leaves the skip link
        hidden."""
        loaded = ran["loaded"]
        assert loaded["ticked"] == [2, 5]
        assert loaded["line"] == occurrences.the_line(12, "q8x2dm", [2, 5])
        assert loaded["copy_off"] is False
        assert loaded["bar_hidden"] is False and loaded["boxes_hidden"] == 0
        assert loaded["skip_hidden"] is False
        assert loaded["log"] == []

    def test_the_line_for_the_boxes_ticked(self, ran):
        """Boxes 3, 7 and 12, ticked in another order, give the line
        exactly, the notes' example; one box the singular; none, no line
        and Copy off, and a click then does nothing."""
        assert ran["none"]["line"] == "" and ran["none"]["copy_off"] is True
        assert ran["three"]["line"] == EXAMPLE
        assert ran["three"]["line"] == occurrences.the_line(
            12, "q8x2dm", [3, 7, 12])
        assert ran["three"]["copy_off"] is False
        assert ran["one"]["line"] == ONE
        assert ran["untick"]["line"] == ""
        assert ran["untick"]["copy_off"] is True
        assert ran["click_without_a_line"]["log"] == []

    def test_past_the_limit_no_line(self, ran):
        """500 ticked give the line; 501, past what one run leaves, give
        none, with Copy off and the limit said."""
        most = occurrences.MAX_OCCURRENCES_LEFT
        assert ran["most"]["line"] == occurrences.the_line(
            12, "q8x2dm", range(1, most + 1))
        assert ran["most"]["copy_off"] is False
        assert ran["past"]["line"] == "" and ran["past"]["copy_off"] is True
        assert str(most) in ran["past"]["count"]
        assert str(most + 1) in ran["past"]["count"]

    def test_copy_asks_the_clipboard_inside_the_click(self, ran):
        """Copy hands the clipboard the line inside the click, as Safari
        asks, once; nothing is selected and the older command is not
        tried."""
        copied = ran["copied"]
        assert copied["log"] == [f"clipboard in the click: {EXAMPLE}"]
        assert copied["status"] and "Cmd+C" not in copied["status"]

    @pytest.mark.parametrize("case", ["refused", "throws", "absent"])
    def test_a_clipboard_refused_or_absent_leaves_the_line_selected(
            self, ran, case):
        """Where the clipboard refuses, fails or is absent, the field is
        focused and its line selected, the older copy command tried, and,
        where that fails too, the bar says to press the keys."""
        said = ran[case]
        assert said["log"][-3:] == ["pick-line focused", "pick-line selected",
                                    "copy command copy"]
        assert "Cmd+C" in said["status"] and "Ctrl+C" in said["status"]
        assert said["line"] == EXAMPLE

    def test_the_older_command_where_it_copies(self, ran):
        """Without a clipboard, the older command's copy is said as
        copied."""
        said = ran["older_command"]
        assert said["log"] == ["pick-line focused", "pick-line selected",
                               "copy command copy"]
        assert said["status"] and "Cmd+C" not in said["status"]
