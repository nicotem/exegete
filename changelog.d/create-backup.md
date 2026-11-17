### Removed

- **`create_backup` is removed, as announced.** Since 0.15.1 the 22
  tools that took it have ignored it, because Exegete takes a backup of
  the project before every change to its database. A call that still
  passes it, with any value, `false` and `null` included, is now
  refused before the tool runs, and nothing is done: the refusal says
  that the argument was removed and to call the tool without it. A host
  that checks a call's arguments against the tool's list before sending
  it refuses the call itself, in its own words. A saved instruction,
  skill or script that passes `create_backup` needs it taken out.
