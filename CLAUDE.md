# CLAUDE.md

Guidance for Claude Code and other AI coding agents working in this
repository. People start with CONTRIBUTING.md; this file adds what an
agent most often gets wrong.

Exegete is a qualitative analysis application used in conversation with
an AI assistant, compatible with QualCoder: its projects keep
QualCoder's format and conventions, so a researcher can work on a
project in either program, one at a time, and its aim is the whole life
of a project from the conversation. It runs as an MCP server.

## Commands

- **Install for development** (Python 3.10 or newer) from the lock,
  the releases CI tests with:
  `uv sync --frozen --extra dev --extra pdf-epub`, which makes `.venv`
  in the repository and installs the package there, editable.
  `pip install -e ".[dev]"` takes the newest releases `pyproject.toml`
  allows instead, as an install from PyPI does.
- **Tests:** `python -m pytest -q` from the repository root. The full
  suite takes about twelve minutes on a Mac, longer on Windows CI; CI
  runs it on Ubuntu, Windows and macOS with Python 3.10 and 3.13 on
  `main` and the integration branches (`feat/*`), and on Ubuntu with
  3.13 alone on other branches (CONTRIBUTING.md, item 5). Every
  behaviour change needs a test that fails without it.
- **Dependencies:** after changing `pyproject.toml`, run `uv lock`, and
  check with `uv lock --check`.
- **The Claude Desktop extension:**
  `python scripts/build_desktop_extension.py --ref HEAD --out DIR`. The
  build is reproducible: the same commit gives the same bytes, dated by
  the commit.

## Where things are

- `src/exegete/server.py`: the MCP server, with its tools, resources,
  prompts, help topics and the assistant's brief. Tool sets: `full`
  and `core` (`EXEGETE_TOOLSET`, or the extension's switch
  (`EXEGETE_SMALL_TOOLSET`)); `lifecycle`, the earlier name of `full`,
  is read as `full`.
- `database.py`: the project database, in QualCoder's format (schema
  v17, as QualCoder 4.0 writes it). `new_project.py`: creating a project.
- `preview_tokens.py`: preview before confirm. `memo_privacy.py`: the
  `#####` private part of memos. `pseudonymise.py`: replacing names.
- `project_settings.py`: the AI coder name file. `state_folder.py`: the
  state folder. `transition.py`: tidying up after the rename.
- `path_identity.py`: containment checks by folder identity.
  `qualcoder_history.py`: a project's history with QualCoder (the
  traces, and the researcher's answer to "Do you also use QualCoder on
  this computer?" or the switch "I use QualCoder on this computer",
  that decide whether a text's notes about QualCoder apply), worked out
  once per selection.
- `doc_import.py`, `doc_readers.py`, `import_reading.py` and their
  neighbours (`import_*.py`, `garbled_text.py`, `kept_texts.py`, the
  text a preview read, kept for its import): bringing documents in
  (`import_documents`, 0.14.3; the optional part
  `pdf-epub` reads PDF and EPUB). `reading.py`, `reading_copy.py`,
  `reading_folder.py`, `opener.py`, `origin_mark.py`: reading a whole
  file on the researcher's screen (`open_file_for_reading`).
  `parts.py`: long files read in parts.
  `private_files.py`: the four kinds of file Exegete keeps, and the
  project's `Exegete` folder for files the researcher fills in (listed,
  never read into an answer).
- `refi_export.py`: REFI-QDA. `coder_comparison.py`: coder agreement.
- `updates.py`: the check for new versions (`check_for_updates` and the
  notes given once). `release.py`: this release's version, date and
  summary, updated with each release.
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
- **No test or probe reaches the network.** The suite refuses any
  connection beyond this computer (`tests/conftest.py`); test the check
  for new versions against a server of your own on 127.0.0.1.
- **Never touch a real QualCoder installation, a real project or any AI
  assistant's configuration.** Tests use fixtures and synthetic data
  only.
- **Tool descriptions are measured.** Tests pin the size sent with every
  request. Rules a model must not miss sit within a description's first
  2,048 characters: Claude Code cut there before its version 2.1.296; it
  now keeps 4,096 (16,384 through tool search), and 2,048 is kept as a
  margin. The few left past it, each with its reason, are listed in
  `LEFT_PAST_THE_CUT` in `tests/test_v0142_description_cut.py`.
- **Documents:** plain UK English, no em dashes. Many sentences in the
  documents are pinned by tests, so move the pin with its sentence.
  Explain risks and suggest alternatives; do not prescribe.
- **Interoperability with QualCoder:** follow QualCoder's formats and
  conventions; name every departure, with its reason; where QualCoder's
  readers lose or garble content, keep it, and name the departure
  (CONTRIBUTING.md's rules on parity and citations; NOTICE lists what
  was taken from QualCoder, and why), without grading QualCoder.
