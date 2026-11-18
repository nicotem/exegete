### For contributors

- **The dates check refuses a reading dated on no day, or after the day
  of the run**, such as "read on 31 November 2026", at release
  preparation (`scripts/check_promises.py`). It lists the first with no
  age and the second with a negative one; it dropped the first without
  a word and never refused the second.
- **The test that no text sends the assistant to a tool or argument that
  does not exist** passes over `search_memo`, the argument search_files
  lost in 0.15.1, only as that word in its own refusal, as it does
  `create_backup`. It passed `search_memo` over in every text.
