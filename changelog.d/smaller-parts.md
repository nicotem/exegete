### Changed

- **A long file comes in smaller parts, each measured as an app
  receives it.** `read_file_with_codings`, the file resource and the
  case resource chose a part's end by an estimate that left the file's
  memo out, so a part of English reached Codex as about 73,600 bytes,
  over the 48,000 that Codex keeps of an answer for the models it lists,
  and lost its middle there. Each answer that serves a part is now
  measured and kept within 40,000 bytes: about 35,000 characters of
  English, or 5,000 to 7,000 of Chinese, Greek, Arabic or Hebrew. Such a
  part reaches Claude Code whole, and Codex whole with the models Codex
  lists (Codex 0.167.0's source, read on 10 November 2026). With any
  other model, such as a local one, Codex keeps about 12,000 bytes of
  an answer. A file whose answer fits comes whole, as before. A longer
  one takes more calls than before: 9 for 300,000 characters of
  English, where it took 5, and 2 for an interview of about an hour
  (55,000 characters), where it took 1.
- **Every part carries the file's memo, and a long memo makes the parts
  shorter.** When what every part from a place carries (the memo, and
  the codings and annotations that reach over the part's start) passes
  20,000 bytes, the part's own text keeps 20,000 bytes and the answer
  passes 40,000: from a memo of about 19,000 characters of English.
- **A coding that runs past the start or end of a part comes in that
  part without its passage**, marked `reaches_beyond_part`, its memo
  kept. In a part, `codes_used` counts the codes of that part's codings;
  `statistics` still count the whole file. The part's note asks the
  assistant to read every part before saying anything about the whole
  file.

### Fixed

- **A long coding no longer makes parts one character long.** A coding
  whose passage alone passed the estimate, about 6,650 characters of
  Chinese, 8,150 to 8,550 of Greek, Arabic or Hebrew, or 70,000 of
  English, made every part from its start one character long, each
  repeating the passage. Such a coding now comes without its passage in
  each part it runs past, and the parts keep their length.

### Documents

- **TOOLS.md** gives a part's size in bytes and characters, what a long
  memo does to it, what Codex keeps of an answer with a model it does
  not list, `reaches_beyond_part` and `codes_used` in a part.
- **The guide to installing from the Terminal** says what Codex keeps of
  an answer with the models it lists and with others, and that it marks
  the middle it leaves out (Codex 0.167.0's source, read on 10 November
  2026). It names two settings that change Codex's budget, neither tried
  by this project: `tool_output_token_limit`, for every tool, and
  `output_token_limit` under
  `[mcp_servers.exegete.tools.read_file_with_codings]`, for that tool
  alone.
