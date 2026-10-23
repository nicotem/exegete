# SPDX-License-Identifier: LGPL-3.0-or-later
"""How many tools each set registers, in one place for every test that
pins the count (v0.15.0, the files design, piece 3).

The names list's pieces move `full` one tool at a time: prepare_names_list
took it from 81 to 82, save_names_list took it to 83, and the removal of
read_pseudonym_list (piece 5) takes it back to 82; v0.15.1 removes
three tools, as announced in 0.14 (export_code_report,
cleanup_old_sessions and merge_proposals), which takes it to 79. Each
changes this line, not a dozen files. A document's own sentence is still read word for
word where a test reads it.
"""

# Every tool, `create_project`, the two earlier names,
# prepare_names_list and save_names_list included
FULL_TOOLS = 79
# The supervised coding set for local models, the two earlier names
# included; restore_backup joined it in v0.15.1 (25 to 26), and
# search_memos (26 to 27), since search_files no longer searches notes
CORE_TOOLS = 27
