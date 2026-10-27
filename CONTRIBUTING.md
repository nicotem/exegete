# Contributing to Exegete

Exegete (formerly qualcoder-mcp) is experimental alpha software maintained by one
researcher. Bug reports, questions, feature ideas and code changes are
all welcome. This file says how to send each, and which rules a change
has to meet before it is merged.

## Reporting issues

Everything goes through
[GitHub Issues](https://github.com/nicotem/exegete/issues): bug
reports, questions and feature ideas alike. There is no email support.
The author's email address in the package metadata is an authorship
signature, not a support channel, and support requests sent there will
not receive a reply. Issues are public and searchable, so every answer
helps the next researcher who hits the same thing. [SUPPORT.md](SUPPORT.md)
has the full policy.

When you report a bug, use the issue template. It asks for the
Exegete version, the QualCoder version if you use QualCoder, the
project's schema version (the `databaseversion` value in the `schema` block that
`get_current_project` returns), your MCP host (Claude Desktop, Claude
Code, LM Studio, other), the toolset (`EXEGETE_TOOLSET`: `core`, or
`full` when the variable is not set; `lifecycle` is the earlier name of
`full`, before 0.15.0) and your operating system.
Never paste participant data, interview text or anything sensitive into
an issue; describe the problem structurally ("a code name with an
apostrophe", "a file of about 40k characters"). Security concerns take
the same route: open an issue, describe the problem structurally, and
say in the title that it concerns data exposure or write safety so it
is looked at first.

## Proposing changes

1. **Open an issue first** for anything beyond a small fix, so the
   scope can be agreed before you write code. The scope rule below
   explains what is likely to be accepted.
2. **Fork and branch.** `main` is never committed to directly; every
   change arrives on a branch and is merged from a pull request against
   `main`.
3. **Install for development** (Python 3.11 or newer):

   ```bash
   git clone https://github.com/<you>/exegete.git
   cd exegete
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -e ".[dev,pdf-epub]"
   ```

   `pdf-epub` is the optional part that reads PDF and EPUB; without it,
   the tests of PDF and EPUB import are skipped. Its libraries are under
   the AGPL (INSTALL.md, "PDF and EPUB: the optional part").

4. **Run the test suite** from the repository root:

   ```bash
   python -m pytest -q
   ```

   The whole suite must pass, on your platform and on the CI. Every new
   behaviour needs a test that fails without the change, including the
   edge cases of any QualCoder behaviour you are matching. Do not add
   skips without a stated reason in the test. One scale test (10k+
   codings, a 500k-character document) is opt-in behind
   `TRACK6_GIANT=1` and is not part of a normal run.
5. **Continuous integration** runs on every pushed branch and on pull
   requests to `main`, in one of two tiers, which its first job, `tier`,
   chooses (`scripts/ci_tier.py` says how). The jobs that run tests,
   all but the one on the newest releases below, install the libraries
   from the lock, `uv.lock`, each release checked against its hash: the
   releases the desktop extension installs, so a new release on PyPI
   cannot turn a job red overnight, and a change to the requirements or
   the version in `pyproject.toml` without `uv lock` fails on the push.
   A push to `main` or to an integration branch, `feat/<name>`, a pull
   request and a run started by hand take the full tier: twenty-two
   jobs. Eleven run the suite: on Python 3.11, the oldest Exegete
   supports, and 3.13, one job each on Ubuntu and on macOS, and three on
   Windows, where the suite is slowest and runs in three parts made of
   whole test files (`tests/conftest.py`); on Python 3.14, the newest,
   one on Ubuntu. To run one part on your own computer, set
   `EXEGETE_TEST_SHARD` to "k/n", such as `2/3` for the second of
   three; left empty, every test runs. Three build the desktop
   extension, one on each system, and install and start it as Claude
   Desktop does (the Linux one also validates it with the official
   MCPB tool and checks that the lock has a wheel for every computer);
   one checks that the three builds are the same bytes. Two compare the
   text the import stores with QualCoder's own extraction: one against
   QualCoder 4.0, and one watching QualCoder's newest code, whose
   changes are a notice, never a failure. Two try the upgrade from the
   package's earlier name, on Ubuntu and on Windows. One checks the
   documents: their links (`scripts/check_links.py`) and the facts
   they repeat (`tests/test_v0151_facts.py`, below); their links to
   other sites are checked once a week instead, by a workflow of its
   own (`external-links.yml`), where a page that is gone fails and a
   site that turns robots away or answers slowly is a notice. One runs
   the suite on Ubuntu with Python 3.13 on the newest release of each
   library `pyproject.toml` allows, what an install from PyPI takes
   today; it may fail and only reports, and its summary gives the
   releases it installed and the newest of each bounded library on
   PyPI. A push to any other branch takes the fast tier: `tier`, the
   suite on Ubuntu with Python 3.13 and the documents job, and the
   desktop extension's jobs as well when the branch changed
   `packaging/`, `pyproject.toml`, `uv.lock` or a script those jobs
   run, counted from where the branch left its integration branch
   (`feat/<p>` for a branch `<p>/<key>`), or else from `main`. Every
   job that runs must be green, the watch and the newest releases
   apart. A change to a workflow, to `pyproject.toml` or to `uv.lock`
   also runs once on the full tier on its own branch before it is
   merged: on GitHub, Actions, then CI, then Run workflow, with the
   branch chosen. The workflow actions are pinned by commit SHA with a
   version comment beside each pin; if you add or bump an action, keep that
   shape (Dependabot maintains the pins). A bump also means recording
   the new SHA against the tag it really is, in `VERIFIED_TAGS` in
   `tests/test_v012_workflow_pins.py`;
   that module's docstring carries the two API calls that resolve it.
   The tests fail on an unrecorded SHA on purpose: Dependabot has left a
   version comment stale beside a bumped SHA before, and nothing else
   checks the comment against upstream. A new job declares the least
   `permissions:` it needs beside itself, and a checkout passes
   `persist-credentials: false` unless the job really uses git
   credentials; both are pinned, and a workflow added as `.yaml`, or a
   composite action under `.github/actions`, is scanned by the same
   ledger.
6. **Document the change.** Add an entry under `Unreleased` in
   `CHANGELOG.md` (Keep a Changelog format). Update the docstring of
   every tool whose arguments or behaviour changed: the docstrings are
   the documentation the AI model reads. A paragraph that several tools
   share, such as the refusal while the project's lock file is active,
   is written once, as a constant in `src/exegete/server.py` that
   `_with_paragraphs` puts back into each of their docstrings, and is
   changed there. Everything Exegete sends the assistant before a
   project is open (the opening text, every tool's description and
   schemas, the prompts, the resources and the brief) is kept in
   `docs/snapshot/`, with the sizes the documents round in
   `sizes.json`, and a test fails when the code and the snapshot
   differ: when you change any of these texts, a tool's arguments or
   the libraries in `uv.lock`, write the snapshot again with
   `python scripts/served_texts.py write` on Python 3.13, in the
   development install, and read its diff whole. Update `TOOLS.md`
   (the tool reference), `README.md`, `INSTALL.md` and `PRIVACY.md` where they
   describe the behaviour you changed; `PRIVACY.md` is the contract for
   what a tool result may disclose. Links are checked on every push
   (`scripts/check_links.py`): when you rename a heading, it names every
   link to it, the update page's included. The facts the documents
   repeat are checked too (`tests/test_v0151_facts.py`): the folders
   (in full example paths too, such as
   `/Users/YOUR_NAME/Exegete projects`), the reading folder, the time
   per import call and the counts against the code's constants; the
   sizes of the tool sets, within five per cent, against
   `docs/snapshot/sizes.json`; the
   libraries' releases against `uv.lock`, and the requirements against
   `pyproject.toml`; the lists of the tools that preview first and of
   those that report signs of a QualCoder window, what PRIVACY.md and
   INSTALL.md say Exegete keeps on the computer, and the map of the
   clone below against the files git tracks; every install command of
   Exegete names the optional part for PDF and EPUB, in its brackets or
   its paragraph; an example in one of QualCoder's own folders has "if
   you use QualCoder" in its paragraph; the extension's settings are
   named by their titles, never by their place in the list; and every
   name a document calls a tool or an argument is one Exegete has. When
   you change one of them in the code, the check names every sentence
   that still gives the old one, in the forms it reads. A release to
   come, named in a document or in a text the code holds (a tool's
   description, a note, a refusal or a log line, as
   `scripts/code_texts.py` reads them), is held to the plan in
   `scripts/release_plan.py`: its sentence names something planned for
   that release, and README's "What comes next" keeps no release
   already made. When a decision moves something to another release,
   change its row in the plan, in the same commit as any text that
   names its new release; at release preparation the rows of that
   release leave the plan. When you remove a tool or an argument, add
   it, with the release, to the test's `RETIRED` table; when you add a
   module or a script, add it to the map.

## Review before merge

Nothing is merged on a green CI alone. Every change also goes through a
QA review and a security review. The QA review checks that each new
behaviour has a test that fails without it, that the edge cases of the
matched QualCoder behaviour are covered, and that the tests are
Windows-safe and encoding-safe. The security review looks at write
paths, file and symlink handling, what a tool result discloses into the
AI conversation, and what a hostile project folder, a hostile model
input or a hostile network response (the version file of the check for
new versions) could make Exegete do or put into the conversation.
Findings from both are fixed and re-verified before the merge, and behaviour changes that come out of them
are recorded in the CHANGELOG. The maintainer runs both reviews; expect
them to take longer than the CI, and expect requests for more tests
rather than fewer.

## Style rules

- **UTF-8 pinned on text IO.** Every `open()` of a text file passes
  `encoding="utf-8"` (or `utf-8-sig` where QualCoder's own export
  dialect writes a BOM). Never rely on the platform default encoding.
- **Windows-safe tests.** Build paths with `pathlib`, build sqlite URIs
  with `Path.as_uri()`, and never assert on identical timestamps or wait
  on the wall clock: fabricate file ages with `os.utime`. Skip cleanly
  where symlinks or POSIX permission bits are unavailable. Spawn the
  server as a subprocess only when the transport or startup gating is
  the thing under test, and give it an explicit environment. The suite
  has to pass on the Windows runner, not only on your machine.
- **No em dashes in prose.** This applies to documentation, docstrings,
  error strings, CHANGELOG entries and commit messages. Use a colon, a
  comma, parentheses or a new sentence.
- **Capability probes, never version strings.** Behaviour keys on the
  existence of tables, columns and views (`SchemaCapabilities` in
  `database.py`), the way QualCoder's own migration ladder does. The
  version string is informational, with one exception: the forward
  guard that refuses writes on a schema newer than the verified ceiling.
- **Parity claims cite the pinned QualCoder commit.** Any statement that
  "QualCoder does X" in a comment, docstring, CHANGELOG entry or
  document names QualCoder's file and line at the pinned commit
  (currently QualCoder master `9bddf17`, version string "QualCoder 4.0
  Beta", whose project format the release keeps). What researchers are
  told Exegete is verified against is the release itself, QualCoder 4.0
  (`VERIFIED_QUALCODER` in `database.py`). When the pin moves, the
  claims are re-verified and re-cited, not carried forward.
- **Heuristics are phrased as heuristics.** A result that reports a
  guess (a project that "appears to be open" in QualCoder) says so.
  Never word a heuristic as a certainty.
- **Disclosure is existence-only.** A tool result may say that
  something exists (a private note on a row, a hidden coder's row, a
  count), never what it contains or whose it is. If a change alters what
  leaves the project into the conversation, or anything Exegete sends
  beyond this computer (an address it contacts, what a request carries,
  when it is made), `PRIVACY.md` changes in the same pull request.
- **No tool argument named `session_id`.** Some MCP middleware strips
  that name before the call reaches the server; the session tools use
  `coding_session_id`. Check new argument names against other
  routing-flavoured names (`request_id`, `conversation_id`, `user_id`,
  `context`, `metadata`) as well.
- **Runtime dependencies stay minimal.** The package has five runtime
  dependencies: the MCP library, `mcp>=1.17.0,<2` (the floor is the
  first release with `FastMCP.remove_tool`, which the core toolset
  needs, and the limit keeps out mcp 2.x, which removed
  `mcp.server.fastmcp`); pydantic and anyio, which the MCP library
  brings and Exegete imports itself; and the two small libraries the
  document import reads with, defusedxml and striprtf. PDF and EPUB
  come through the optional part `pdf-epub`. A new dependency needs a
  reason in the pull request; anything optional must stay optional and
  import-guarded (the way `psutil` is used). A library Exegete imports
  is named among its requirements (`tests/test_v0151_libraries.py`
  checks). Such a library, or one the MCP library loads at start
  without a limit of its own, takes an upper limit at its next major
  release when it is large or fast-moving, so an install from PyPI
  meets a new major release only with a release of Exegete tried with
  it. Not bounded today: cryptography (never loaded by Exegete, held per
  computer by `[tool.uv]`), onnxruntime and numpy (which PyMuPDF 2
  brings on Windows x64 and Linux; large, but loaded only inside the
  reading process, never at Exegete's start, where Exegete's own code
  imports onnxruntime only to switch its usage reports off; a new major
  release of either could stop PDFs being read
  there, which the `newest-libraries` job would show), pywin32
  (Windows only), uvicorn, python-multipart and sse-starlette (a limit
  at their next minor release would hold back routine fixes),
  defusedxml, striprtf (already exact), EbookLib (small, about one
  release a year) and Starlette (neither large nor imported by
  Exegete). If you change a dependency or a limit in `pyproject.toml`,
  regenerate `uv.lock` with `uv lock` in the same commit, so that
  `uv lock --check` passes and the lock file agrees with the package.
- **Synthetic test data only.** Never commit a `.qda` project, a real
  transcript or any research text. Test fixtures are built in code.
- **British English in all prose.** Documentation, docstrings, tool
  and prompt descriptions, error strings, result notes, CHANGELOG
  entries and commit messages use British spelling (behaviour, colour,
  analyse, organise, initialise, licence as a noun). Identifiers are
  never changed: tool names (`recolor_code`), argument names
  (`sanitize_formulas`), JSON result keys, environment
  variable names, file names, SQL, and proper names such as "GNU
  Lesser General Public License" keep their exact spelling, including
  when a sentence mentions them. Code comments follow the same rule when a line is
  touched.

## How the server is built

```
┌──────────────────────────────┐
│  MCP host (Claude Desktop,   │
│  Claude Code, LM Studio ...) │
└──────────────┬───────────────┘
               │ MCP protocol (stdio)
               │
┌──────────────▼───────────────┐
│  Exegete                     │  (this package)
│  exegete                     │
└──────────────┬───────────────┘
               │ SQLite connection (read-only by default;
               │  guarded writes with backup, lock and
               │  heuristic open-window checks)
               │
┌──────────────▼───────────────┐
│  The project database, in    │
│  QualCoder's format          │
│  (data.qda, in the .qda      │
│  project folder)             │
└──────────────────────────────┘
```

### Project structure

```
exegete/                     # the clone (its folder's name does not matter)
├── src/
│   ├── exegete/                 # the package (its module is `exegete`)
│   │   ├── __init__.py
│   │   ├── names.py             # Every name the program goes by, typed once
│   │   ├── env_settings.py      # The settings, read under both spellings
│   │   ├── state_folder.py      # The state folder and its one move
│   │   ├── server.py            # Main MCP server with resources, tools, prompts
│   │   ├── database.py          # SQLite database interface
│   │   ├── file_kinds.py        # What kind of entry sits at a name: a named pipe is refused, never opened (0.15.1)
│   │   ├── memo_privacy.py      # QualCoder's '#####' private-memo convention
│   │   ├── new_project.py       # create_project: the folder and its schema v17 database
│   │   ├── sessions.py          # AI coding session management
│   │   ├── project_settings.py  # The project's AI coder name (exegete.json)
│   │   ├── preview_tokens.py    # Preview tokens for the destructive tools
│   │   ├── path_identity.py     # Whether a path is inside a folder, by the folder's identity
│   │   ├── qualcoder_history.py # A project's history with QualCoder, worked out once per selection (0.15.0)
│   │   ├── doc_import.py        # import_documents: the survey, the preview and the write (0.14.3)
│   │   ├── doc_readers.py       # Each format's text, as QualCoder 4.0 reads it, with every departure named
│   │   ├── import_reading.py    # The separate, short-lived process each document is read in
│   │   ├── kept_texts.py        # The text a preview read, kept owner-only for its import (0.15.0)
│   │   ├── import_paths.py      # Where documents may be imported from
│   │   ├── import_words.py      # What the import says, in fixed plain words
│   │   ├── import_page.py       # The page for checking letters that look garbled
│   │   ├── garbled_text.py      # Letters that came out wrong, read back through common sets
│   │   ├── reading.py           # open_file_for_reading: native first (0.14.3)
│   │   ├── reading_copy.py      # The reading page: a file's whole text and its codings
│   │   ├── reading_folder.py    # The private reading folder, and its tidying
│   │   ├── opener.py            # Opening a file in its own app, or showing it in its folder
│   │   ├── private_files.py     # The files Exegete keeps, and the project's Exegete folder (0.15.0)
│   │   ├── names_file.py        # The names file: its five lines, and how it is read back (0.15.0)
│   │   ├── origin_mark.py       # The internet-origin mark, carried to a copy
│   │   ├── parts.py             # Whole-file reads in parts
│   │   ├── cursors.py           # Paging cursors for the search and segment tools
│   │   ├── coder_comparison.py  # compare_coders: agreement and the two kappas
│   │   ├── pseudonymise.py      # pseudonymise_source: matching, remapping, the residue detector
│   │   ├── refi_export.py       # REFI-QDA XML export
│   │   ├── transition.py        # --check-transition: what the move from qualcoder-mcp left
│   │   ├── updates.py           # The check for new versions: check_for_updates, the notes given once
│   │   └── release.py           # This release's version, date and summary, for the note after an update
│   └── qualcoder_mcp/           # the earlier name's two-file stand-in
├── scripts/
│   ├── ci_tier.py              # Which tier of CI a run takes, and whether the extension's jobs run
│   ├── build_desktop_extension.py  # Builds the Claude Desktop extension (.mcpb)
│   ├── smoke_desktop_extension.py  # Installs and starts a built extension as Claude Desktop does
│   ├── check_pages_site.py     # Checks the update site against this release
│   ├── check_links.py          # Checks the links in the documents (other sites once a week)
│   ├── release_plan.py         # What comes in which release: the table the texts are held to
│   ├── code_texts.py           # The texts the package's code holds, read without running it
│   ├── check_advisories.py     # Asks OSV's database of advisories about every release in the lock
│   ├── served_texts.py         # What Exegete sends the assistant before a project is open, and the brief, written to docs/snapshot/ or compared with it
│   ├── extension_libraries.py  # What the desktop extension installs on each computer, as one table
│   ├── compare_release_surface.py  # Compares what two releases offer an assistant and a researcher
│   ├── release_version.py      # What a published release builds, read from its tag
│   ├── practice_version.py     # A practice version of both packages for a TestPyPI rehearsal
│   ├── qualcoder_parity.py     # What QualCoder's own import stores from each test document
│   ├── make_timing_documents.py  # Made-up Word files for timing how long an import's preview reads
│   ├── structure_table.py      # The structural table kept per release in docs/structure/
│   └── create_test_project.py  # Test project generator
├── docs/
│   ├── brand/                  # Exegete's mark
│   ├── history/                # Early plans and analyses, kept as a record
│   ├── snapshot/               # What Exegete sends the assistant before a project is open, and the brief, with their sizes
│   └── update-check/           # The design of the check for new versions, as a record
├── pages/                   # The update site: latest.json and the update page
├── packaging/
│   ├── desktop-extension/      # The extension's manifest template and its validator
│   └── pypi-old-name/          # The old name's package, qualcoder-mcp, released until v1.0
├── legal/
│   └── GPL-3.0.txt         # The GNU GPL, version 3, which the LGPL incorporates
├── pyproject.toml           # Package configuration
├── README.md               # What it is, where data goes, how to start
├── TOOLS.md                # Every tool, what it reads and writes
├── CHANGELOG.md            # Version history
├── INSTALL.md              # Detailed installation guide
├── PRIVACY.md              # Data-flow disclosure
├── CONTRIBUTING.md         # How to report, propose and review changes
├── CITATION.cff            # Citation metadata
├── SUPPORT.md              # Support policy (GitHub Issues only)
├── COPYING.LESSER          # The licence: GNU LGPL, version 3
└── NOTICE                  # Copyright, licence, and the code derived from QualCoder
```

### Using MCP Inspector for development

For development and debugging, you can use the MCP Inspector:

```bash
# Install uv if you haven't already
pip install uv

# Run the inspector
export EXEGETE_PROJECT_PATH="/path/to/your/project.qda"
uv run --with "mcp[cli]" mcp dev src/exegete/server.py
```

This will open a web interface where you can test resources and tools.
The server is built on the
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Scope

The design is for general use, principles first. A feature is justified
on general grounds: the whole life of a project from the conversation;
interoperability with QualCoder, its formats and conventions kept and
every departure named; general mappings that hold for any project;
capability probes rather than special cases. Requests that fit only one research project, one
researcher's habits or one MCP host are usually declined or generalised
first. The same rule applies to the maintainer's own projects.

## The earlier name

The program was called qualcoder-mcp until 0.14.0. Its Python module
is now `exegete` (every runtime name is in `src/exegete/names.py`), and
a local clone's folder name does not matter. Two things keep the
earlier name working for people who already use it:

- `packaging/pypi-old-name/` is the old name's package on PyPI: the
  `qualcoder-mcp` command and a two-file stand-in module, depending on
  `exegete`. It is built and uploaded with every release until v1.0, by
  the same workflow and in the same step (`publish.yml`), at the same
  version; tests keep its version, its floor on `exegete`, its licence
  files and its stand-in equal to the main ones. At v1.0 its last
  release says plainly that it is the last, and none follows.
- `src/qualcoder_mcp/` is the same stand-in, kept in the source for
  copies of it; it hands over to `exegete.server:main`, which is
  therefore never removed or renamed. The `exegete` wheel never holds
  it (`pyproject.toml` says why).

An early build of a coming release, to hold the name on PyPI before the
release is ready, is a GitHub pre-release tagged with the release's
version from `pyproject.toml` plus `.devN` (for example
`v0.14.1-alpha.dev1`, which uploads `exegete` 0.14.1a0.dev1). It builds
and uploads `exegete` alone, never the old name's package, so an
upgrade through the old name never brings unfinished work; any tag
other than `v<version>` or `v<version>.devN` stops the workflow before
it builds anything (`scripts/release_version.py`).

## The check for new versions

Every installed copy with checking on fetches
`https://nicotem.github.io/exegete/latest.json` (`src/exegete/updates.py`)
and follows no redirect, so that address is permanent: never rename or
delete the `nicotem` account, the `exegete` repository or its Pages
site, and never set a custom domain on this
Pages site or on the account's own one (GitHub would then redirect, and
every copy would stop hearing of new versions). The file keeps
`"format": 1`; a change it cannot keep is published beside it under
another name. Each release updates `src/exegete/release.py` (the
version, its date and the summary the note after an update shows) with
`pyproject.toml` and the CHANGELOG heading; tests hold the three
together. The file, and the update page Exegete's notes point to
(`https://nicotem.github.io/exegete/update/`), live in `pages/`, and
each release updates both with `release.py` (`latest.json`'s version as
PyPI spells it, its date, and the page's version, date, summary, links
and commands); `tests/test_v0142_pages.py` holds them to `release.py`.
Each release's notes on GitHub list what the desktop extension
installs, under "What the extension installs": the table in the summary
of the Linux desktop extension job in the release commit's CI run
(`scripts/extension_libraries.py`, from the lock's dry run on each
computer). The site is published by `.github/workflows/pages.yml`,
deployed from GitHub Actions and never from a branch (the owner's decision of 5
October 2026, `docs/update-check/design.md`, D3): a branch would let
any token that can push rewrite `latest.json` without a release. Once
the release is published, with its extension file, and both packages
are on PyPI, start the workflow by hand from the release's tag. It
checks the site against the release (`scripts/check_pages_site.py`)
and that the release is out, and the deploy waits in the
`github-pages` environment for the owner's approval: the last step of
each release, and a hold switch for a bad file.

## The record on Zenodo

Zenodo archives each GitHub release, describes it from `.zenodo.json`
alone and not from `CITATION.cff` (`tests/test_v0151_zenodo.py` keeps
the two in step), and submits the record to the Exeter Data Studies
community (`datastudies`), whose curators accept the request on
Zenodo, unless the community's review policy lets its owners publish
without review.

## Licence

From v0.13, Exegete (then called qualcoder-mcp) is licensed under the GNU Lesser General
Public License, version 3 or (at your option) any later version
(LGPL-3.0-or-later): see [COPYING.LESSER](COPYING.LESSER) and
[legal/GPL-3.0.txt](legal/GPL-3.0.txt), the GNU General Public
License text it incorporates. Releases up to 0.12.1 were published
under the MIT License. By contributing you agree that your contribution
is licensed under the same terms.

Every `.py` file under `src/`, `tests/` and `scripts/` opens with the line
`# SPDX-License-Identifier: LGPL-3.0-or-later` (after a shebang or an
encoding line, where the file has one), and `tests/test_licence.py`
fails without it, so a new module needs it from its first commit.

QualCoder is licensed under LGPL-3.0-or-later as well, and the rule for
its code is the owner's (2026-09-23):

- **Write our own implementation by default,** and prove parity with
  tests against QualCoder's source. Cite QualCoder's file and line you
  matched in the docstring.
- **Copy QualCoder's code only where identical results cannot be had
  otherwise,** as with the kappa expression, whose floating-point
  result depends on the order of its operations, and the coding
  editor's span walk.
- **List every copy in [NOTICE](NOTICE) with its reason:** its file and
  function here, the QualCoder file and lines it comes from, and why it
  had to be copied. A test that carries QualCoder's code as its oracle
  is listed there too, and `tests/test_licence.py` fails if a file or
  name NOTICE gives no longer exists, so a rename or a rewrite updates
  NOTICE in the same change. It also holds NOTICE's entries as a
  snapshot, so an entry is removed only by editing the test as well.

Most of the items NOTICE lists were copied before this rule was made;
some of them could be written afresh, and each is kept as it is until
its code is next changed.
