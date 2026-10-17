# SPDX-License-Identifier: LGPL-3.0-or-later
"""How many tools each set registers, in one place for every test that
pins the count (v0.15.0, the files design, piece 3).

The names list's pieces move `full` one tool at a time: prepare_names_list
took it from 81 to 82, save_names_list takes it to 83, and the removal of
read_pseudonym_list back to 82. Each changes this line, not a dozen
files. A document's own sentence is still read word for word where a
test reads it.
"""

# Every tool, `create_project`, the two earlier names and
# prepare_names_list included
FULL_TOOLS = 82
# The supervised coding set for local models, the two earlier names
# included
CORE_TOOLS = 25
