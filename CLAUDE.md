# CLAUDE.md

Guidance for Claude Code and other AI coding agents working in this
repository. People start with CONTRIBUTING.md; this file adds what an
agent most often gets wrong.

## Commands

- **Install for development** (Python 3.10 or newer):
  `pip install -e ".[dev]"`.
- **Tests:** `python -m pytest -q` from the repository root. The full
  suite takes about ten minutes; CI runs it on Ubuntu, Windows and macOS
  with Python 3.10 and 3.13. Every behaviour change needs a test that
  fails without it.
- **Dependencies:** after changing `pyproject.toml`, run `uv lock`, and
  check with `uv lock --check`.
- **The Claude Desktop extension:**
  `python scripts/build_desktop_extension.py --ref HEAD --out DIR`. The
  build is reproducible: the same commit gives the same bytes, dated by
  the commit.

## Where things are

- `src/exegete/server.py`: the MCP server, with its tools, resources,
  prompts, help topics and the assistant's brief. Tool sets: `full`,
  `core` and `lifecycle` (`EXEGETE_TOOLSET`).
- `database.py`: QualCoder's SQLite project (schema v17, as QualCoder
  4.0 writes it). `new_project.py`: creating a project.
- `preview_tokens.py`: preview before confirm. `memo_privacy.py`: the
  `#####` private part of memos. `pseudonymise.py`: replacing names.
- `project_settings.py`: the AI coder name file. `state_folder.py`: the
  state folder. `transition.py`: tidying up after the rename.
- `path_identity.py`: containment checks by folder identity.
- `refi_export.py`: REFI-QDA. `coder_comparison.py`: coder agreement.
- README ("For advanced users") and CONTRIBUTING.md have the full map.

## Rules for agents

- **Never run the server, a probe or a manual check with your real home
  folder.** The first start moves `~/.qualcoder_mcp` to `~/.exegete` and
  writes there. Point `HOME`, `USERPROFILE`, `EXEGETE_STATE_HOME`,
  `QUALCODER_MCP_STATE_HOME`, `TMPDIR` and `UV_CACHE_DIR` at a scratch
  folder. The test suite isolates itself (`tests/conftest.py`); your own
  runs do not.
- **Commit with an explicit identity** (`git -c user.name=...
  -c user.email=... commit`) whenever `HOME` points somewhere else.
  Otherwise git silently invents an address from the machine's name, and
  that address becomes public once pushed.
- **Never touch a real QualCoder installation, a real project or any AI
  assistant's configuration.** Tests use fixtures and synthetic data
  only.
- **Tool descriptions are measured.** Tests pin the size sent with every
  request. Rules a model must not miss sit within a description's first
  2,048 characters, because Claude Code cuts there.
- **Documents:** plain UK English, no em dashes. Many sentences in the
  documents are pinned by tests, so move the pin with its sentence.
  Explain risks and suggest alternatives; do not prescribe.
- **Parity with QualCoder:** follow QualCoder's own behaviour, and name
  every departure with its reason (CONTRIBUTING.md, NOTICE).
