### Changed

- In Claude Code, the parts of a long file that `read_file_with_codings`
  gives now reach the conversation as text. The tool declares a result
  limit of 200,000 characters; Claude Code saved an answer longer than
  50,000 characters to a file under `~/.claude/projects/` and gave the
  assistant its path instead.

### Documents

- TOOLS.md and the Terminal guide warn that Codex 0.166.0 gives the
  model about 48,000 bytes of a tool's answer and leaves out its middle,
  so with Codex the middle of a part of a long file can be missed.
