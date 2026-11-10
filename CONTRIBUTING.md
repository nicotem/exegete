# Contributing to Exegete

Exegete (formerly qualcoder-mcp) is experimental alpha software maintained by one
researcher. Bug reports, questions, feature ideas and code changes are
all welcome. This file says how to send each, and which rules a change
has to meet before it is merged.

## Reporting issues

Bug reports, questions and ideas for features all go through
[GitHub Issues](https://github.com/nicotem/exegete/issues). Requests
for support sent by email receive no reply. Issues are public and
searchable, so every answer helps the next researcher with the same
problem. [SUPPORT.md](SUPPORT.md) gives the whole policy.

When you report a bug, use the issue template. It asks for the facts
about your setup that SUPPORT.md lists under "Before you report", and
for your operating system. An issue is public, so participants' data or
a project put into one is published with it. Describe the data without
copying it instead, such as "a code name with an apostrophe" or "a file
of about 40,000 characters". SUPPORT.md says what a log can hold.
A security concern, such as a fault that could expose participants'
data or let a write damage a project, is best reported privately, as
[SECURITY.md](SECURITY.md) describes, so that it is not public before
its fix. Describe it there without copying data, as above.

## Proposing changes

1. **Open an issue first** for anything beyond a small fix, so the
   scope can be agreed before you write code. The scope rule below
   explains what is likely to be accepted.
2. **Fork and branch.** Make your change on a branch of your fork, and
   send it as a pull request against `main`.
3. **Install for development** (Python 3.11 or newer):

   <!-- ci: run dev -->
   ```bash
   git clone https://github.com/<you>/exegete.git
   cd exegete
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -e ".[dev,pdf-epub]"
   ```

   `pdf-epub` is the optional part that reads PDF and EPUB. Without it,
   the tests of PDF and EPUB import are skipped. Its libraries are under
   the AGPL (INSTALL.md, "PDF and EPUB: the optional part").

   On Windows x64, Linux and Macs with Apple silicon, the part brings
   PyMuPDF 2, which loads onnxruntime, Microsoft's library for running
   trained models. onnxruntime reports on its own use to Microsoft
   unless it is switched off. On Linux and macOS, its own setting,
   `ORT_DISABLE_TELEMETRY=1`, given before it loads, switches the
   reports off. Exegete's reading process, the suite
   (`tests/conftest.py`) and `scripts/qualcoder_parity.py` give that
   setting. An import of PyMuPDF anywhere else, such as your own check
   of what is installed, does not. On a Mac with Apple silicon, with
   onnxruntime 1.31.0, such an import made onnxruntime write a device id
   and a database of events into the home folder, in
   `Library/Application Support/Microsoft/DeveloperTools/.onnxruntime`.
   That measurement did not check whether anything was sent. You can
   give the setting yourself before you start Python, with
   `export ORT_DISABLE_TELEMETRY=1` in the Terminal. On Windows,
   onnxruntime does not read the setting:
   [PRIVACY.md, "How your data flows"](PRIVACY.md#how-your-data-flows),
   says what it reports there.

4. **Run the test suite** from the repository root:

   ```bash
   python -m pytest -q
   ```

   The whole suite must pass on your platform and in CI, the checks
   that step 5 describes. Every new behaviour needs a test that fails
   without the change, including the edge cases of any QualCoder
   behaviour you are matching. Do not add skips without a stated reason
   in the test. Two scale tests are not part of a normal run. They share one build, a project with more than
   10,000 codings and a document of 500,000 characters, made only when
   `TRACK6_GIANT=1` is set. The suite gives each test a home folder
   of its own, inside pytest's temporary folder (`tests/conftest.py`).
   At the end of a run, the suite fails if a test created anything in
   your own folders for projects. It also fails if a test changed
   `~/.exegete`, the folder where Exegete keeps its working files, or
   `~/.qualcoder_mcp` from before the rename. A copy of Exegete that you
   are running at the same time can change that folder too, so stop it
   before you run the suite.
5. **Continuous integration** (CI) is the set of checks GitHub runs on
   every pushed branch and on pull requests to `main`. It runs in one of
   two tiers, and its first job, `tier`, chooses which
   (`scripts/ci_tier.py` says how). Every job that runs tests, except
   the one on the newest releases described below, installs the
   libraries from the lock, `uv.lock`, and checks each release against
   its hash. These are the releases the desktop extension installs, so a
   new release on PyPI cannot turn a job red overnight. A change to the
   requirements or to the version in `pyproject.toml` fails on the push
   unless `uv lock` was run with it.

   A push to `main` or to an integration branch, `feat/<name>`, a pull
   request and a run started by hand take the full tier: twenty-two
   jobs.
   - Eleven run the suite. On Python 3.11, the oldest Exegete supports,
     and on 3.13, the suite runs in one job each on Ubuntu and on macOS,
     and in three on Windows. The suite is slowest on Windows, so there
     it runs in three parts made of whole test files
     (`tests/conftest.py`). On Python 3.14, the newest, it runs in one
     job, on Ubuntu. To run one part on your own computer, set
     `EXEGETE_TEST_SHARD` to "k/n", such as `2/3` for the second of
     three. When it is empty, every test runs.
   - Three build the desktop extension, one on each system, and install
     and start it as Claude Desktop does. The Linux one also validates
     it with the official MCPB tool, and checks that the lock has a
     wheel for every computer. One more checks that the three builds are
     the same bytes.
   - One compares the text the import stores with the text QualCoder
     4.0's own extraction gives. It also reads QualCoder 4.0's source
     for two more facts. The first is that QualCoder's backup copies a
     project's Exegete folder. The second is that QualCoder's import,
     when it applies the names list that Exegete saves, gives the text
     that Exegete stores.
   - Two try the upgrade from the package's earlier name, on Ubuntu and
     on Windows.
   - One checks the documents: their links (`scripts/check_links.py`),
     their texts (`scripts/check_texts.py`, under Style rules), the
     facts they repeat (`tests/test_v0151_facts.py`, below) and the
     snapshot (`tests/test_served_texts.py`, step 6). Its summary also
     lists the documents' promises and dated readings
     (`scripts/check_promises.py`, step 6). Their links to
     other sites are checked once a week instead, by a workflow of its
     own, `external-links.yml`. There, a page that is gone fails, and a
     site that turns robots away or answers slowly is a notice.
   - One runs the commands the documents mark, each set in a new, empty
     home folder, and compares what they print with what the documents
     say. `scripts/doc_commands.py` says how to mark a command. This
     job installs Exegete from the commit, and the newest releases of
     its libraries from PyPI, as the documents' commands do. So it may
     fail, and only reports.
   - One runs the suite on Ubuntu with Python 3.13, on the newest
     release of each library that `pyproject.toml` allows, which is what
     an install from PyPI takes today. It may fail, and only reports. Its
     summary gives the releases it installed, and the newest release on
     PyPI of each library that has an upper limit.
   - The twenty-second is `tier` itself.

   A push to any other branch takes the fast tier: `tier`, the suite on
   Ubuntu with Python 3.13, and the documents job. The desktop
   extension's jobs run as well when the branch changed `packaging/`,
   `pyproject.toml`, `uv.lock` or a script those jobs run. The branch's
   changes are counted from where it left its integration branch
   (`feat/<p>` for a branch `<p>/<key>`), or else from `main`. Every
   job that runs must be green, apart from the two that only report.

   Two more checks run once a week, on Mondays, each in a workflow of
   its own, and also on a push that changes that workflow.
   `advisories.yml` asks OSV's database of advisories about every
   release in `uv.lock` and in the official validator's lock,
   `packaging/desktop-extension/validator/package-lock.json`. It also
   runs on a push that changes its script or either lock. A new advisory
   fails. One already accepted, with its date and reason in
   `scripts/check_advisories.py`, is a notice. `qualcoder-watch.yml`
   runs the test files of the comparison with QualCoder 4.0, above,
   against QualCoder's newest code. It is red when one of them fails
   there, as it does when that code stores a different text, and the
   maintainer reads a red run that day.

   A change to a workflow, to `pyproject.toml` or to `uv.lock` also runs
   once on the full tier, on its own branch, before it is merged. To
   start that run on GitHub, open Actions, then CI, then Run workflow,
   and choose the branch.

   Each action a workflow uses is pinned to a commit SHA, with a comment
   beside the pin that gives its version. If you add or bump an action,
   keep that form. Dependabot keeps the pins up to date. A bump also
   needs two more steps. First, record the new SHA against the tag it
   really is, in `VERIFIED_TAGS` in `tests/test_v012_workflow_pins.py`.
   That module's docstring gives the two API calls that resolve it.
   Second, name the action with its new version in the change log's
   current entry, the file that step 6 describes. The newest entry that
   names an action must name the version it is pinned at. The tests
   fail on an unrecorded SHA on purpose: Dependabot has left a version
   comment stale beside a bumped SHA before, and nothing else checks the
   comment against upstream. A new job declares, in its own definition,
   the least `permissions:` it needs. A checkout passes
   `persist-credentials: false` unless the job really uses git
   credentials. The same tests check both. They also read a workflow
   added as `.yaml`, and a composite action under `.github/actions`.
6. **Document the change.** Describe it for the CHANGELOG in a file of
   its own, `changelog.d/<key>.md`. `<key>` is your branch's name
   without any prefix before a slash. Make the folder if it is absent.
   Never edit `CHANGELOG.md`. When a release is prepared,
   `scripts/assemble_changelog.py` writes the release's entry from
   these files and deletes them, so two changes never edit the same
   lines. The file holds one or more sections, each under one of these
   headings, in this order. First come the six that Keep a Changelog
   names: `### Added`, `### Changed`, `### Deprecated`, `### Removed`,
   `### Fixed` and `### Security`. Then come `### Documents`, and
   `### For contributors` for CI, scripts and tests. Under each, write
   as the CHANGELOG does, and give every link its whole address: a
   relative link would lead nowhere once the text moves.

   The measurement of what Exegete sends to the app that starts it is
   kept in one file that every change shares, `changelog.d/measured.md`.
   It is the only place for `### Measured`, and holds nothing else. The
   first change that moves a size writes it, and each later one amends
   it. When two such changes are written at the same time, the second
   to merge measures again. A change may amend or remove an earlier
   file of the same release that it supersedes, saying so in its pull
   request. A change made without a branch of its own, such as a
   dependency update, adds a file named for its subject in the same
   commit. A test may check facts from the code, but never the words of
   these files, which the release deletes.

   Update the docstring of every tool whose arguments or behaviour
   changed: the docstrings are the descriptions the assistant reads.
   Some paragraphs are shared by several tools, such as the refusal
   while the project's lock file is active. Each is written once, as a
   constant in `src/exegete/server.py`, and `_with_paragraphs` puts it
   back into each tool's docstring, so a change to it is made there.
   Three tool texts also give the lock paragraph's words, typed by hand:
   - `apply_codings`' safety guarantees
   - `restore_backup`'s list of safeguards
   - the key features in `explain_ai_coding_tools`' overview

   Six texts give a shorter form of the same rule:
   - the brief, which `read_brief` returns
   - the descriptions of `select_project` and `set_project_coder_name`
   - `get_current_project`'s account of `qualcoder_open`
   - `start_coding_session`'s paragraph on a project in use
   - `import_documents`' list of what it refuses

   Rule 9 of the opening text says what the assistant does when a tool
   reports another program. When the rule's words change, change them in
   each of these texts too.

   For each tool set, `full` and `core`, `docs/snapshot/` keeps the
   texts Exegete gives the assistant that are the same for every
   project:
   - the opening text
   - each tool's description, the schemas of its arguments and of its
     answer, its annotations and its marks under `_meta`
   - the prompts, with their texts
   - the resources and resource templates, with the texts of the two
     guidance resources
   - the brief, which `read_brief` returns

   No other tool's answer is in it.
   `docs/snapshot/sizes.json` gives the sizes that the documents round,
   and a test fails when the code and the snapshot differ. When you
   change any of these texts, a tool's arguments or the libraries in
   `uv.lock`, write the snapshot again. Run
   `python scripts/served_texts.py write` on Python 3.13, with the
   releases of mcp and pydantic that `uv.lock` gives, and read its diff
   whole. The install of step 3 may take newer releases.
   `uv sync --frozen --extra dev --extra pdf-epub` installs the lock's
   releases, and on a Mac with Apple silicon it needs macOS 14 or
   later.

   Update `TOOLS.md` (the tool reference), `README.md`, `INSTALL.md`,
   the Terminal guide (`docs/installing-from-the-terminal.md`) and
   `PRIVACY.md` where they describe the behaviour you changed.
   `PRIVACY.md` is the contract for what a tool result may disclose.
   Links are checked on every push, by `scripts/check_links.py`. When
   you rename a heading, the script lists every link to it, the update
   page's included.

   The facts the documents repeat are checked too, by
   `tests/test_v0151_facts.py`. It checks:
   - the folders, in full example paths too (such as
     `/Users/YOUR_NAME/Exegete projects`), the reading folder, the time
     per import call and the counts, against the code's constants
   - the sizes of the tool sets, against `docs/snapshot/sizes.json`,
     within five per cent
   - the libraries' releases, against `uv.lock`, and the requirements,
     against `pyproject.toml`
   - the list of the tools that preview a change first, and the list of
     those that report whether QualCoder 4.0 may have the project open
   - what PRIVACY.md, INSTALL.md and the Terminal guide say Exegete
     keeps on the computer
   - the map below: its lists of the package's modules and of the
     scripts must give exactly the Python files that git tracks in
     `src/exegete/` and `scripts/`
   - that every install command of Exegete names the optional part for
     PDF and EPUB, in its brackets or in its paragraph
   - that an example in one of QualCoder's own folders has "if you use
     QualCoder" in its paragraph
   - that the extension's settings are called by their titles, never by
     their place in the list
   - that every name a document gives a tool or an argument is one that
     Exegete has

   When you change one of these facts in the code, the check lists every
   sentence that still gives the old one, in the forms it reads.

   A release to come may be named in a document, or in a text the code
   holds. Such a text is a tool's description, a note, a refusal or a
   log line, as `scripts/code_texts.py` reads them. The check compares
   each such mention with the plan in `scripts/release_plan.py`. The
   sentence that names the release must name something the plan gives to
   that release. When the sentence names nothing in the plan, its
   paragraph must, and each list item counts as a paragraph of its own.
   Something from the plan that is named beside a release to come must
   be named beside the release the plan gives it. README's "What comes
   next" must give no release already made. When a decision moves
   something to another release, change its row in the plan in the same
   commit as any text that gives its new release. At release preparation, the rows of that
   release leave the plan. When you remove a tool or an argument, add
   it, with the release, to the test's `RETIRED` table.

   Every push also lists the documents' promises and their dated
   readings of other programs, in the documents job's summary
   (`scripts/check_promises.py`). A promise says that something is
   still to come, in words such as `not yet` or `is planned`. The list
   gives each promise's line, the day that line was written, as
   `git blame` gives it, and the row of the plan that its sentence or
   paragraph names. A dated reading gives the day a claim about another
   program was checked, in the form [docs/WRITING.md](docs/WRITING.md)
   gives, and the list gives its age in days. At release preparation,
   `python scripts/check_promises.py --release`, run in a full clone,
   fails on a promise whose line is older than the script's
   `MAX_AGE_DAYS` and that names no row of the plan, and on a reading
   older than `MAX_AGE_DAYS`. Write what is missing as what Exegete
   does not do, or give it a row in the plan. A sentence that uses a
   promise's words for a state, such as
   `a change previewed but not yet made`, goes into the script's
   `NOT_PROMISES`, with its reason.

## Review before merge

Nothing is merged on a green CI alone. Every change also goes through a
QA review and a security review. The QA review checks that each new
behaviour has a test that fails without it. It checks that the edge
cases of the QualCoder behaviour being matched are covered, and that
the tests are safe on Windows and with any text encoding. The security
review looks at write paths, file and symlink handling, and what a tool
result discloses into the conversation. It also asks what a hostile
project folder, hostile input from the assistant or a hostile network
response could make Exegete do or put into the conversation. The network
response here is the version file of the check for new versions.
Findings from both are fixed and re-verified before the merge, and
behaviour changes that come out of them are recorded in the CHANGELOG.
The maintainer runs both reviews. Expect them to take longer than the
CI, and expect requests for more tests rather than fewer.

## Style rules

- **UTF-8 for every text file.** Every `open()` of a text file passes
  `encoding="utf-8"` (or `utf-8-sig` where QualCoder's own export
  dialect writes a BOM). Never rely on the platform default encoding.
- **Windows-safe tests.** Build paths with `pathlib`, build sqlite URIs
  with `Path.as_uri()`, and never assert on identical timestamps or wait
  on the wall clock: fabricate file ages with `os.utime`. Skip cleanly
  where symlinks or POSIX permission bits are unavailable. Start
  Exegete as a subprocess only when the transport or startup gating is
  the thing under test, and give it an explicit environment. The suite
  has to pass on the Windows runner, not only on your machine.
- **The writing guide.** [docs/WRITING.md](docs/WRITING.md) says who
  reads Exegete's texts and how to write them: the documents, the
  screens a researcher sees and the texts the assistant receives.
- **No em dashes in prose.** This applies to documentation, docstrings,
  error strings, CHANGELOG entries and commit messages. Use a colon, a
  comma, parentheses or a new sentence.
- **The texts check.** `python scripts/check_texts.py` reads the
  documents and the texts in the code, and fails on three kinds of
  sentence. The first mentions QualCoder outside three cases: a
  sentence about QualCoder itself or its format, a sign that QualCoder
  is in use, and a choice the researcher may make. The second asks
  everyone to close QualCoder. The third shows one of the plainest
  habits of style to leave out, such as an exclamation mark, a word of
  praise or a word of our own work like "pinned". Each habit is an
  entry of `VOICE`, at the head of the script. Rewrite the sentence the
  check reports. A few phrases are never accepted, whatever the reason:
  the entries of `FRAMES`, beside `VOICE`. A reader can accept any
  other sentence that is right as it stands, with a reason. The command
  `python scripts/check_texts.py --accept "<reason>" --file <file>`
  adds a line for each finding in that file to
  `scripts/check_texts_ledger.tsv`, and the review reads every line
  added. A line whose reason begins with "seeded" holds a sentence that
  no reader has read yet. `--list seeded --file <file>` prints those
  sentences. A reader replaces the reason by hand with their own, and
  `--prune` removes the lines of sentences rewritten since.
  `--readability` prints each document's measures, which never make the
  check fail. At release preparation, `--release` also fails while a
  seeded line is left in README.md, QUICKSTART.md, the update page or
  the extension's manifest.
- **Capability probes, never version strings.** Exegete decides what it
  can do from the tables, columns and views a project has
  (`SchemaCapabilities` in `database.py`), the way QualCoder's own
  migration ladder does. The version string only informs, with one
  exception: the forward guard, which refuses writes on a schema newer
  than the newest one Exegete is verified against.
- **Claims about QualCoder cite QualCoder's code.** Any statement that
  "QualCoder does X" in a comment, docstring, CHANGELOG entry or
  document gives QualCoder's file and line, and the commit or release
  they were read at. The code's citations stay at one commit, QualCoder
  master `9bddf17`, until they are read again. That commit's version
  string is "QualCoder 4.0 Beta", and the 4.0 release keeps its project
  format. Newer citations may cite the release, tag `4.0` at `b95e021`.
  The documents tell researchers that Exegete is verified against the
  release itself, QualCoder 4.0 (`VERIFIED_QUALCODER` in `database.py`).
  When the commit cited changes, the claims are verified and cited
  again, not carried forward.
- **Heuristics are phrased as heuristics.** A result that reports a
  guess (a project that "appears to be open" in QualCoder) says so.
  Never word a heuristic as a certainty.
- **Disclosure is existence-only.** A tool result may say that
  something exists (a private note on a row, a hidden coder's row, a
  count), never what it contains or whose it is. If a change alters what
  passes from the project into the conversation, `PRIVACY.md` changes
  in the same pull request. It changes too when a change alters anything
  Exegete sends beyond this computer: an address it contacts, what a
  request carries, or when a request is made.
- **No tool argument named `session_id`.** In August 2026, Anthropic's
  bridge to remote devices removed an argument of that name before the
  call reached Exegete (the CHANGELOG's entry for 0.10.1). So the
  session tools use `coding_session_id`. Check a new argument's name
  against the other names a host may use for its own routing as well:
  `request_id`, `conversation_id`, `user_id`, `context` and `metadata`.
- **Runtime dependencies stay minimal.** The package has five runtime
  dependencies. The first is the MCP library, `mcp>=1.17.0,<2`. Its
  lower limit is the first release with `FastMCP.remove_tool`, which
  the core tool set needs. Its upper limit keeps out mcp 2.x, which
  removed `mcp.server.fastmcp`. Then come pydantic and anyio, which the
  MCP library brings and Exegete imports itself, and the two small
  libraries the document import reads with, defusedxml and striprtf.
  PDF and EPUB come through the optional part `pdf-epub`. A new
  dependency needs a reason in the pull request. Anything optional must
  stay optional, behind a guarded import, the way `psutil` is used. A
  library Exegete imports is named among its requirements
  (`tests/test_v0151_libraries.py` checks). Such a library takes an
  upper limit at its next major release when it is large or changes
  fast. So does a library that the MCP library loads at start without a
  limit of its own. Then an install from PyPI takes a library's new
  major release only once a release of Exegete has been tried with it.
  These libraries have no upper limit today:
  - cryptography, which Exegete never loads. `[tool.uv]` keeps it, on
    each computer, to a release that has a wheel there;
  - onnxruntime and numpy, which PyMuPDF 2 brings on Windows x64, Linux
    and Macs with Apple silicon. They are large, but they are loaded
    only inside the reading process, never at Exegete's start. In the
    reading process, Exegete's own code imports onnxruntime only to
    switch its usage reports off. On Windows, onnxruntime makes a few
    reports as it loads, before the switch can be reached, and
    PRIVACY.md, "How your data flows", says what they hold. A new major
    release of either could stop PDFs being read there, which the
    `newest-libraries` job would show;
  - pywin32, on Windows only;
  - uvicorn, python-multipart and sse-starlette, since a limit at their
    next minor release would hold back routine fixes;
  - defusedxml;
  - striprtf, already required at one exact release;
  - EbookLib, which is small and has had six releases since 2018, the
    latest on 1 November 2026 (PyPI, read on 4 November 2026);
  - and Starlette, neither large nor imported by Exegete.

  If you change a dependency or a limit in `pyproject.toml`, run
  `uv lock` in the same commit to write `uv.lock` again. Then
  `uv lock --check` passes, and the lock file agrees with the package.
- **Synthetic test data only.** Never commit a `.qda` project, a real
  transcript or any research text. Test projects are built in code. The
  files under `tests/fixtures/` hold no research data. They are made-up
  documents for the import's tests, most of them saved by other
  programs, and records kept as JSON, such as the facts of a new
  project made in QualCoder 4.0. The REFI-QDA standard's own schema is
  there too.
- **British English in all prose.** Documentation, docstrings, tool
  and prompt descriptions, error strings, result notes, CHANGELOG
  entries and commit messages use British spelling (behaviour, colour,
  analyse, organise, initialise, licence as a noun). Identifiers keep
  their exact spelling, even when a sentence mentions them. They
  include tool names (`recolor_code`), argument names
  (`sanitize_formulas`), JSON result keys, environment variable names,
  file names and SQL. Proper names, such as "GNU Lesser General Public
  License", keep theirs too. Code comments follow the same rule when a
  line is touched.

## How Exegete is built

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

The map below shows the files and folders at the top of the
repository, the package's modules and the scripts. Two tests check it
against the files that git tracks. The facts check, above, checks its
lists of modules and scripts against the Python files in
`src/exegete/` and `scripts/`. `tests/test_v0153_project_map.py`
checks the rest. Every path in the map must be one that git tracks,
but `changelog.d/`, which a release's preparation leaves empty until
the next change adds its file (step 6). Each file or folder at the top
must be in the map, or in the test's list of those it leaves out, with
its reason. When a change adds, moves
or removes one of them, change the map in the same commit.

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
│   │   ├── change_record.py     # The record each change leaves for undo; a sweep removes it once a day old
│   │   ├── undo.py              # undo_changes: the plan, its refusals and the write-back (0.15.2)
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
│   │   ├── reading.py           # open_file_for_reading: the reading page by default, or a read-only copy of the original, shown in its folder or opened in its own app (0.14.3)
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
│   │   ├── occurrences.py       # pseudonymise_source: the short id and line number of each occurrence of a name, and the page for choosing them (0.15.3); each occurrence's number, the list's numbering and the page's one script (0.15.4)
│   │   ├── refi_export.py       # REFI-QDA XML export
│   │   ├── transition.py        # --check-transition: what the move from qualcoder-mcp left
│   │   ├── updates.py           # The check for new versions: check_for_updates, the notes given once
│   │   ├── standard_input.py    # Standard input, read a line at a time in a daemon thread, so that one Ctrl+C stops Exegete
│   │   ├── standard_output.py   # Standard output, as the MCP library writes it: what Exegete tells once counts as told once its answer has gone out (0.15.3)
│   │   └── release.py           # This release's version, date and paragraph on what is new, for the note after an update and the update page
│   └── qualcoder_mcp/           # the earlier name's two-file stand-in
├── tests/                   # The suite, and conftest.py, which gives each test a home folder of its own
│   └── fixtures/               # Made-up documents and records for the tests, and the REFI-QDA standard's schema
├── scripts/
│   ├── ci_tier.py              # Which tier of CI a run takes, and whether the extension's jobs run
│   ├── build_desktop_extension.py  # Builds the Claude Desktop extension (.mcpb)
│   ├── assemble_changelog.py   # Writes a release's CHANGELOG entry from changelog.d/
│   ├── smoke_desktop_extension.py  # Installs and starts a built extension as Claude Desktop does
│   ├── check_pages_site.py     # Checks the update site against this release
│   ├── check_links.py          # Checks the links in the documents (other sites once a week)
│   ├── check_texts.py          # Checks the texts for mentions of QualCoder and for the voice
│   ├── check_texts_ledger.tsv  # The sentences a reader has accepted as they stand
│   ├── check_promises.py       # Lists the documents' promises and dated readings, and refuses old ones at release preparation
│   ├── doc_commands.py         # Runs the commands the documents mark, and checks what they print
│   ├── release_plan.py         # What comes in which release: the table the texts are held to
│   ├── code_texts.py           # The texts the package's code holds, read without running it
│   ├── check_advisories.py     # Asks OSV's database of advisories about every release in uv.lock and the validator's lock
│   ├── served_texts.py         # The texts Exegete gives the assistant that are the same for every project, written to docs/snapshot/ or compared with it
│   ├── extension_libraries.py  # What the desktop extension installs on each computer, as one table
│   ├── compare_release_surface.py  # Compares what two releases offer an assistant and a researcher
│   ├── release_version.py      # What a published release builds, read from its tag
│   ├── practice_version.py     # A practice version of both packages for a TestPyPI rehearsal
│   ├── qualcoder_parity.py     # What QualCoder's own import stores from each test document
│   ├── make_timing_documents.py  # Made-up Word files for timing how long an import's preview reads
│   ├── structure_table.py      # The structural table kept per release in docs/structure/
│   └── create_test_project.py  # Test project generator
├── changelog.d/             # The next release's CHANGELOG entry, in files of their own (step 6)
├── docs/
│   ├── brand/                  # Exegete's mark
│   ├── installing-from-the-terminal.md  # Installing from the Terminal: every route but the desktop extension
│   ├── snapshot/               # The texts Exegete gives the assistant that are the same for every project, with their sizes
│   ├── structure/              # The structural table of each release (scripts/structure_table.py)
│   ├── update-check/           # The design of the check for new versions, as a record
│   └── WRITING.md              # The writing guide: who reads Exegete's texts, and how to write them
├── pages/                   # The update site: latest.json and the update page
├── packaging/
│   ├── desktop-extension/      # The extension's manifest template and its validator
│   └── pypi-old-name/          # The old name's package, qualcoder-mcp, released until v1.0
├── legal/
│   └── GPL-3.0.txt         # The GNU GPL, version 3, which the LGPL incorporates
├── .github/                 # The workflows GitHub runs, the issue forms and Dependabot's settings
├── pyproject.toml           # Package configuration
├── uv.lock                  # The libraries' lock: each library's release, with its hashes
├── MANIFEST.in             # What the source distribution leaves out: the tests and the earlier name's files
├── README.md               # What it is, where data goes, how to start
├── QUICKSTART.md           # Exegete set up by hand in Claude Desktop
├── TOOLS.md                # Every tool, what it reads and writes
├── AI_CODING_GUIDE.md      # Coding with the assistant, step by step, with example conversations
├── PROJECT_SELECTION_GUIDE.md  # Choosing the project Exegete works on, for installs from the Terminal
├── CHANGELOG.md            # Version history
├── INSTALL.md              # Installing the desktop extension for Claude Desktop
├── PRIVACY.md              # Where your data goes, and who can read it there
├── CONTRIBUTING.md         # How to report, propose and review changes
├── CLAUDE.md               # For AI coding agents: what they most often get wrong here
├── CITATION.cff            # Citation metadata
├── .zenodo.json            # How Zenodo describes each release it archives
├── SUPPORT.md              # Support policy (GitHub Issues only)
├── SECURITY.md             # How to report a security fault privately
├── COPYING.LESSER          # The licence: GNU LGPL, version 3
└── NOTICE                  # Copyright, licence, and the code derived from QualCoder
```

### Trying the tools in the MCP Inspector

The MCP Inspector is a page in your browser from which you call a
server's tools, prompts and resources by hand. It starts Exegete as an
app would. It needs Node.js 22.19.0 or newer and runs through `npx`, as
its page, <https://modelcontextprotocol.io/docs/tools/inspector>, says
(read on 4 November 2026). In the environment of step 3:

```bash
npx @modelcontextprotocol/inspector python -m exegete.server
```

The MCP library's own command, `mcp dev src/exegete/server.py`, cannot
start Exegete. It loads `server.py` as a file on its own, and the
module's imports are relative to its package.

Started from the Inspector, Exegete works in your own home folder, as it
does however it is started. It keeps its working files in `~/.exegete`,
and looks for projects in the usual places. If an earlier copy left a
folder at `~/.qualcoder_mcp`, the first start moves it to `~/.exegete`.
The pages and copies that Exegete opens for reading go into its reading
folder, and a reading page holds a document's whole text and its
codings.
[PRIVACY.md](PRIVACY.md#reading-a-whole-file-what-leaves-the-computer)
says where that folder is. To try the tools away from your own projects
and these folders, start the Inspector with `HOME` set to an empty
folder, as the suite does for each test. On Windows, set `USERPROFILE`
to the same folder and `LOCALAPPDATA` to a folder inside it. On Linux,
unset `XDG_CACHE_HOME` or set it inside that folder.

Exegete also reads its settings from the environment it starts in. A
project or a folder for projects set there would point the trial at
your real projects, so leave out every setting whose name begins with
`EXEGETE_` or `QUALCODER_`, as the suite does. `tests/conftest.py`
shows how. Then make a made-up project there with
`scripts/create_test_project.py`, which takes the path of a new folder
ending in `.qda`, and select it by that path. In the page,
`list_available_projects` and `select_project` choose a project.
Exegete is built on the
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Scope

The design is for general use, principles first. A feature is justified
on general grounds:

- the whole life of a project from the conversation
- interoperability with QualCoder, its formats and conventions kept and
  every departure named
- general mappings that hold for any project
- capability probes rather than special cases

Requests that fit only one research project, one researcher's habits or
one MCP host are usually declined or generalised first. The same rule
applies to the maintainer's own projects.

## The earlier name

The program was called qualcoder-mcp until 0.14.1, the release that
renamed it. Its Python module
is now `exegete` (every runtime name is in `src/exegete/names.py`), and
a local clone's folder name does not matter. Two things keep the
earlier name working for people who already use it:

- `packaging/pypi-old-name/` is the old name's package on PyPI: the
  `qualcoder-mcp` command and a two-file stand-in module, depending on
  `exegete`. It is built and uploaded with every release until v1.0, at
  the same version, by the same workflow and in the same step
  (`publish.yml`). Tests keep its version, its floor on `exegete`, its
  licence files and its stand-in equal to the main ones. At v1.0 its
  last release says plainly that it is the last, and none follows.
- `src/qualcoder_mcp/` is the same stand-in, kept in the source for
  copies of it. It hands over to `exegete.server:main`, which is
  therefore never removed or renamed. The `exegete` wheel never holds
  it (`pyproject.toml` says why).

An early build of a coming release can hold the name on PyPI before the
release is ready. It is a GitHub pre-release, tagged with the release's
version from `pyproject.toml` plus `.devN`: for example,
`v0.14.1-alpha.dev1` uploads `exegete` 0.14.1a0.dev1. It builds and
uploads `exegete` alone, never the old name's package, so an upgrade
through the old name never brings unfinished work. Any tag other than
`v<version>` or `v<version>.devN` stops the workflow before it builds
anything (`scripts/release_version.py`).

## The check for new versions

Every installed copy with checking on fetches
`https://nicotem.github.io/exegete/latest.json` (`src/exegete/updates.py`)
and follows no redirect, so that address must never change. Never rename or
delete the `nicotem` account, the `exegete` repository or its Pages
site, and never set a custom domain on this Pages site or on the
account's own one. Each of these would remove the site or move it to
another address, and every copy would stop hearing of new versions. A
custom domain set for the account's own site is used for all its
project sites as well (GitHub's page on custom domains, read on
4 November 2026). The file keeps
`"format": 1`; a change it cannot keep is published beside it under
another name.

Each release updates `src/exegete/release.py` with `pyproject.toml` and
the CHANGELOG heading: the version, its date, and the paragraph that
the note after an update gives (`SUMMARY`). Tests hold the version and
the date to the other two. The paragraph is written by hand at release
preparation, from the CHANGELOG entry's opening and its "Upgrading
from" part. It says what is new for a researcher and what changes for
them, such as what to do and what behaves differently. It is one plain
paragraph of at most 800 characters, with no link, no Markdown and no
line break; the note adds the link to the release's notes on GitHub.
A test holds the length and the line break, and refuses a link,
Markdown's marks for a link, bold, code and a heading, and an HTML tag.
It lets a single `*` or `_` through, since a name such as
`update_check.json` holds one, so reading the paragraph is what keeps
out Markdown's emphasis. No test can tell whether the paragraph describes this
release or the last one, so this step is the only guard. Read the note
whole before the release, as the assistant will receive it: its frame
is `_after_update_text` in `src/exegete/updates.py`.

The version file, and the update page Exegete's notes point to
(`https://nicotem.github.io/exegete/update/`), live in `pages/`. Each
release updates both with `release.py`. `latest.json` gets the version
as PyPI spells it, and its date. The page gets the version, its date,
the links and the commands, and, under "What's new", the same paragraph
as the note, word for word. `tests/test_v0142_pages.py` holds them to
`release.py`.

Exegete tells some things once: the check's disclosure, a new version,
and the note after an update. The first two can come on another tool's
answer or in `check_for_updates`' own. Each is recorded as told only
after the answer carrying it has been written to standard output and
flushed (`src/exegete/standard_output.py`). It is not recorded when the
app has cancelled the request. Every tool but `check_for_updates` runs
on the event loop, so the library reads a cancel only once such a tool
has answered, and that answer still goes out. Standard input's own thread
(`src/exegete/standard_input.py`) reads the line after the call while
such a tool runs, and gives it to `standard_output.read_cancel`, so a
cancel sent next is known before the answer goes out. A cancel sent
behind several other lines is read only once the tool has answered,
and can come too late: the note then counts as given.
This relies on the MCP library flushing standard output once each
message has been written: a message written in two parts, or two
messages to one flush, are read alike. A release of the library that
stopped flushing would leave every note held: each would come again at
every start, and with checking on, the disclosure would never be
recorded, so the check would never run.
`tests/test_v0153_update_note.py` holds this, and the
`newest-libraries` job, which runs the suite on the newest releases,
is where such a change would show first.

Each release's notes on GitHub list what the desktop extension
installs, under "What the extension installs". The list is the table
that `scripts/extension_libraries.py` writes from the lock's dry run on
each computer. It is in the summary of the Linux desktop extension job,
in the CI run of the release's commit.

The site is published by `.github/workflows/pages.yml`,
deployed from GitHub Actions and never from a branch (the maintainer's
decision of 5 October 2026, recorded in `docs/update-check/design.md`):
a branch would let any token that can push rewrite `latest.json`
without a release. Once the release is published, with its extension
file, and both packages are on PyPI, start the workflow by hand from
the release's tag. It checks the site against the release
(`scripts/check_pages_site.py`) and that the release is out. The deploy
then waits in the `github-pages` environment for the maintainer's
approval: the last step of each release, and a hold switch for a bad
file.

## The record on Zenodo

Zenodo archives each GitHub release of a connected repository. When
both `.zenodo.json` and `CITATION.cff` are present, it describes the
release from `.zenodo.json` alone (Zenodo's help pages, read on
4 November 2026). `tests/test_v0151_zenodo.py` keeps the two files in
step. Zenodo submits the record to the community that `.zenodo.json`
gives, the Exeter Data Studies community (`datastudies`). The
community's curators accept the request on Zenodo, unless its review
policy lets the account that submits the record publish without
review.

## Licence

From v0.13, Exegete (then called qualcoder-mcp) is licensed under the
GNU Lesser General Public License, version 3 or (at your option) any
later version (LGPL-3.0-or-later). Its text is in
[COPYING.LESSER](COPYING.LESSER), and
[legal/GPL-3.0.txt](legal/GPL-3.0.txt) holds the GNU General Public
License, whose text it incorporates. Releases up to 0.12.1 were
published under the MIT License. By contributing you agree that your
contribution is licensed under the same terms.

Every `.py` file under `src/`, `tests/` and `scripts/` opens with the
line `# SPDX-License-Identifier: LGPL-3.0-or-later`, after a shebang or
an encoding line where the file has one. `tests/test_licence.py` fails
without it, so a new module needs it from its first commit.

QualCoder is licensed under LGPL-3.0-or-later as well, and the rule for
its code is the maintainer's (23 September 2026):

- **Write our own implementation by default,** and prove parity with
  tests against QualCoder's source. Cite QualCoder's file and line you
  matched in the docstring.
- **Copy QualCoder's code only where identical results cannot be had
  otherwise,** as with the kappa expression, whose floating-point
  result depends on the order of its operations.
- **List every copy in [NOTICE](NOTICE) with its reason:** its file and
  function here, the QualCoder file and lines it comes from, and why it
  had to be copied. A test that carries QualCoder's code as its oracle
  is listed there too. `tests/test_licence.py` fails if a file or a
  name that NOTICE gives no longer exists, so a rename or a rewrite
  updates NOTICE in the same change. It also holds NOTICE's entries as
  a snapshot, so an entry is removed only by editing the test as well.
  NOTICE has a copy in `packaging/pypi-old-name/`, which a test holds
  equal to it, byte for byte, so a change goes into both.

Most of the items NOTICE lists were copied before this rule was made;
some of them could be written afresh, and each is kept as it is until
its code is next changed.
