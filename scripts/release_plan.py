# SPDX-License-Identifier: LGPL-3.0-or-later
"""What comes in which release: the plan Exegete's texts are held to
(v0.15.2).

Data only, read by the facts check (tests/test_v0151_facts.py): a text in
the documents or in the code that names a release to come must name an
item planned for it, and an item named beside a release to come must be
named beside its own. When a decision moves an item, change its row: the
push names every sentence that still gives the old release. A text
written ahead of its release needs its row in the same commit. At release
preparation each row of that release leaves PLANNED, into the check's
RETIRED table when it is a tool or an argument, and README's "What comes
next" keeps no release already made. README's section stays the account
for researchers; this table is the one the checks read.
"""

# The releases to come that a text calls by a name, as "the release on
# method"
RELEASES = {"0.15.4": "method", "0.16": "chat-first"}

# One row for each thing that comes or goes: its kind (tool, argument,
# earlier name or feature); its release, a version or "later" when none
# is set; the words that name it in a text (patterns, read in any letter
# case, each with a sentence in the facts check's tests); and the owner's
# rulings it follows, by number, or "roadmap" when no ruling has set it.
# The rows of ruling 41, the rename's, keep the release that
# names.OLD_SPELLINGS_UNTIL gives.
PLANNED = {
    "undo": ("feature", "0.15.2", (r"\bundo\b",), "88, 105"),
    "the occurrences choice": ("feature", "0.15.2", (
        r"\bwhich\s+mentions\s+to\s+keep\b", r"\boccurrences\s+choice\b"),
        "85, 105, 106"),
    "the REFI-QDA fix": ("feature", "0.15.2", (
        r"\bREFI-QDA\s+(?:export\s+)?fix",
        r"\bfix(?:es|ed)?\s+(?:to\s+)?(?:the\s+)?REFI-QDA\b"), "85, 105"),
    "PyMuPDF 2.0 on Apple silicon": ("feature", "0.15.2", (
        r"\bApple\s+silicon\b",), "98, 105, 107"),
    "coding sessions kept with their project": ("feature", "0.15.3", (
        r"\bsessions\s+(?:are\s+)?kept\s+with\s+(?:their|the|its)\s+"
        r"project",), "85, 105"),
    "the housekeeping that touches data": ("feature", "0.15.3", (
        r"\bhousekeeping\b",), "85, 105"),
    "the review of method": ("feature", "0.15.4", (
        r"\bsupports\s+a\s+study's\s+method\b", r"\breview\s+of\s+method\b"),
        "85, 105"),
    "shorter tool descriptions": ("feature", "0.15.4", (
        r"\bshorte(?:r|ned)\s+(?:tool\s+)?descriptions\b",), "104, 105"),
    "the two tools' earlier names": ("earlier name", "0.15.4", (
        r"\bearlier\s+names\b", r"\banalyze_for_coding\b",
        r"\banalyze_file_with_coding\b"), "73, 85, 105"),
    "create_backup": ("argument", "0.15.4", (
        r"\bcreate_backup\b", r"\bbackup\s+option\b"), "85, 105"),
    "the analysis shown in the conversation": ("feature", "0.16", (
        r"\bshown\s+in\s+the\s+conversation\b", r"\btables\s+and\s+graphs\b"),
        "roadmap"),
    "PDFs that say where their text came from": ("feature", "0.16", (
        r"\bwhere\s+their\s+text\s+came\s+from\b",), "roadmap"),
    "fuller counts of the names left": ("feature", "0.16", (
        r"\bwhere\s+names\s+remain\b",), "roadmap"),
    "a user manual": ("feature", "0.17", (r"\buser\s+manual\b",), "roadmap"),
    "codings placed by the passage they quote": ("feature", "0.17", (
        r"\bplaced\s+by\s+the\s+passage\b",), "roadmap"),
    "the old name's package": ("earlier name", "1.0", (
        r"\bold\s+name's\s+package\b",
        r"\bearlier\s+name's\s+last\s+release\b",
        r"\blast\s+release\s+of\s+this\s+package\b",
        r"\breleased\s+beside\s+(?:every\s+)?Exegete\b",
        r"\bold\s+(?:command|way\s+of\s+starting)\b"), "41"),
    "the earlier spellings": ("earlier name", "1.0", (
        r"\bearlier\s+spellings?\b", r"\bold\s+setting\s+spellings\b",
        r"\bearlier\s+setting\s+names\b",
        r"\bspellings?\s+of\s+(?:one|a|the|this)\s+setting\b",
        r"\bQUALCODER_MCP_", r"\bQUALCODER_PROJECT_PATH\b"), "41"),
    "lifecycle": ("earlier name", "1.0", (r"\blifecycle\b",), "41, 73"),
    "qualcoder_mcp.json": ("earlier name", "1.0", (
        r"\bqualcoder_mcp\.json\b",), "41"),
    "the qualcoder:// addresses": ("earlier name", "1.0", (
        r"\bqualcoder://", r"\bearlier\s+addresses\b",
        r"\bold\s+resource\s+addresses\b"), "41"),
    "a sandbox for the reading process": ("feature", "later", (
        r"\bsandbox\b",), "roadmap"),
    "the evaluation of local models": ("feature", "later", (
        r"\bevaluat(?:e|ed|ion\s+of)\s+local\s+models\b",), "roadmap"),
    "coding images, audio and video": ("feature", "later", (
        r"\bcoding\s+images\b",), "roadmap"),
    "more QualCoder 4.0 conventions": ("feature", "later", (
        r"\bQualCoder\s+4\.0\s+conventions\b",), "58"),
}
