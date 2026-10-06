# CLAUDE.md

Guidance for Claude Code and other AI coding agents working in this
repository. People start with CONTRIBUTING.md; this file adds what an
agent most often gets wrong.

## Commands

- **Install for development** (Python 3.10 or newer):
  `pip install -e ".[dev]"`.
- **Tests:** `python -m pytest -q` from the repository root. The full
  suite takes about twelve minutes on a Mac, longer on Windows CI; CI
  runs it on Ubuntu, Windows and macOS with Python 3.10 and 3.13. Every behaviour change needs a test that
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
- CONTRIBUTING.md ("Project structure") has the full map of
  `src/exegete`, and the README's "For advanced users" a short one.
  Tests are in `tests/`, and the build, release and helper scripts in
  `scripts/`.

## Rules for agents

- **Never run the server, a probe or a manual check with your real home
  folder.** The first start moves `~/.qualcoder_mcp` to `~/.exegete` and
  writes there. The server finds that folder through the home folder
  alone, so `HOME` (and `USERPROFILE`, for Windows) is what protects it:
  point both at a scratch folder, with `TMPDIR` and `UV_CACHE_DIR`. The
  test suite isolates itself (`tests/conftest.py`); your own runs do
  not.
- **Commit with an explicit identity** (`git -c user.name=...
  -c user.email=... commit`) whenever `HOME` points somewhere else.
  Otherwise git makes up an address from the machine's name, prints a
  notice and commits anyway, and that address becomes public once
  pushed.
- **Never touch a real QualCoder installation, a real project or any AI
  assistant's configuration.** Tests use fixtures and synthetic data
  only.
- **Tool descriptions are measured.** Tests pin the size sent with every
  request. Rules a model must not miss sit within a description's first
  2,048 characters, because Claude Code cuts there; the few left past the
  cut, each with its reason, are listed in `LEFT_PAST_THE_CUT` in
  `tests/test_v0142_description_cut.py`.
- **Documents:** plain UK English, no em dashes. Many sentences in the
  documents are pinned by tests, so move the pin with its sentence.
  Explain risks and suggest alternatives; do not prescribe.
- **Parity with QualCoder:** follow QualCoder's own behaviour, and name
  every departure with its reason (CONTRIBUTING.md's rules on parity and
  citations; NOTICE lists what was taken from QualCoder, and why).
