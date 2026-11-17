### Removed

- **The earlier names of the two tools renamed in 0.15.0 are removed,
  as announced.** `analyze_for_coding` (now `start_coding_session`) and
  `analyze_file_with_coding` (now `read_file_with_codings`) are no
  longer listed in either tool set: `full` registers 78 tools and
  `core` 26. A call of an earlier name is refused as a call of a tool
  that does not exist, and nothing is done. A choice your host saved
  for an earlier name, to run it without asking or to block it, no
  longer applies, and a saved instruction, skill or script that calls
  one needs the new name. INSTALL.md's count of the tools that only
  add, which Codex runs without asking under its default, is 17, where
  it was 18.
