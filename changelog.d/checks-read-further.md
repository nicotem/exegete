### For contributors

- **The dates check refuses a reading whose date is no day**, such as
  "read on 31 November 2026", at release preparation, and lists it with
  no age; it dropped such a reading without a word.
- **Two checks read further.** The test that no text sends the assistant
  to a tool or argument that does not exist passes over `search_memo`,
  the argument search_files lost in 0.15.1, only in its own refusal, as
  it does `create_backup`. The test that `server.py` writes
  no text of its own also reads a `match` case, an item or an attribute
  that is set, a walrus and a `for` statement's target.
