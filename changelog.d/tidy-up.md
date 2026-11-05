### Documents

- The two guides to coding with the assistant are now one,
  [AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md).
  It takes from AI_CODING_WORKFLOW.md what it did not already say, and
  says each thing once:
  - each step of a session, with what to say and what comes back
  - the two example conversations
  - where the folder for projects is, and what a sync service can do to
    it
  - how the review finds the earlier speaker turn
  - what Exegete checks, in order, before it applies codings
  - sessions and backups
  - answers to common problems

  AI_CODING_WORKFLOW.md is removed, and the links to it in TOOLS.md and
  SUPPORT.md lead to the guide.
- The guide gives the choices for a coded passage's length as
  `start_coding_session` asks them: a phrase, whole sentences, or a
  whole paragraph or answer. The workflow guide gave only a whole
  answer. The guide's account of what an interpretive reading may draw
  on no longer presumes that your documents are interviews. Near its
  start, the guide now says that what the assistant reads through
  Exegete passes through the conversation to the AI provider, unless
  the assistant runs on your own computer. It points to PRIVACY.md for
  more.
- The early plans, analyses, research notes and security review kept
  in `docs/history/` since 0.15.1 are no longer among the repository's
  files. Git's history keeps them, and the folder is still there at the
  tag of 0.15.2-alpha:
  <https://github.com/nicotem/exegete/tree/v0.15.2-alpha/docs/history>.
  NOTICE, in both packages, gives the address there of each of the
  three items it lists from them. The CHANGELOG's earlier entries that
  mention the folder are records, and keep their words.
- `example_config.json`, an early example configuration that no
  document mentioned, is removed.

### For contributors

- CONTRIBUTING.md's map of the clone now lists every file and folder at
  the top of the repository but `.gitignore`. `tests/`, `changelog.d/`,
  `.github/`, `uv.lock`, `MANIFEST.in`, QUICKSTART.md,
  AI_CODING_GUIDE.md, PROJECT_SELECTION_GUIDE.md, CLAUDE.md and
  `.zenodo.json` join it, and `docs/WRITING.md` joins the documents
  under `docs/`. The line for `occurrences.py` now mentions the page for
  choosing occurrences, which the module builds.
- `tests/test_v0153_project_map.py` checks the map against the files
  that git tracks. Every path in the map must be one that git tracks.
  Each file or folder at the top must be in the map, or in the test's
  list of those it leaves out, with its reason.
- `scripts/check_promises.py` no longer lists `docs/history/` among
  the folders it leaves unread. The tests that read or mentioned the
  folder or the workflow guide follow the change.
  `tests/test_v0151_history_folder.py` now checks that the folder is
  gone and that NOTICE's addresses lead to the tag. In a clone that has
  the tag, it also checks the folder there.
