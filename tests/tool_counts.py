# SPDX-License-Identifier: LGPL-3.0-or-later
"""How many tools each set registers, in one place for every test that
pins the count (v0.15.0, the files design, piece 3).

Read from docs/snapshot/sizes.json (v0.15.2, the snapshot), which
scripts/served_texts.py writes from the code and
tests/test_served_texts.py holds to it, so that a tool added or removed
changes the snapshot, written again by the script, and no count typed
here or in another test. A document's own sentence is still read word
for word where a test reads it, and the counts the documents give are
held by tests/test_v0151_facts.py.
"""
import json
from pathlib import Path

# Every set's sizes, as the snapshot gives them
SNAPSHOT_SIZES = json.loads((Path(__file__).resolve().parents[1] / "docs"
                             / "snapshot" / "sizes.json").read_text(
                                 encoding="utf-8"))
# Every tool, `create_project`, the two earlier names,
# prepare_names_list and save_names_list included
FULL_TOOLS = SNAPSHOT_SIZES["full"]["tool_count"]
# The supervised coding set for local models, the two earlier names
# included
CORE_TOOLS = SNAPSHOT_SIZES["core"]["tool_count"]
