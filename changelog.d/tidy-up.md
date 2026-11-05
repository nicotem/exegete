### Documents

- The two guides to coding with the assistant are now one,
  [AI_CODING_GUIDE.md](https://github.com/nicotem/exegete/blob/main/AI_CODING_GUIDE.md).
  It takes from AI_CODING_WORKFLOW.md what it did not already say: each
  step of a session, with what to say and what comes back; the two
  example conversations; where the folder for projects is, and what a
  sync service can do to it; how the review finds the earlier speaker
  turn; what Exegete checks, in order, before it applies codings;
  sessions and backups; and answers to common problems. Each of these
  is said once. AI_CODING_WORKFLOW.md is removed, and the links to it
  in TOOLS.md and SUPPORT.md lead to the guide.
- The guide gives the choices for a coded passage's length as
  `start_coding_session` asks them: a phrase, whole sentences, or a
  whole paragraph or answer, where the workflow guide gave a whole
  answer alone. What an interpretive reading may draw on no longer
  takes it that your documents are interviews.
- The early plans, analyses, research notes and security review kept
  in `docs/history/` since 0.15.1 are no longer among the repository's
  files. Git's history keeps them, and the folder is at the tag of
  0.15.2-alpha:
  <https://github.com/nicotem/exegete/tree/v0.15.2-alpha/docs/history>.
  NOTICE, in both packages, gives the three items it lists from them
  by their addresses there. The CHANGELOG's earlier entries that name
  the folder are records, and keep their words.
- `example_config.json`, an early example configuration that no
  document named, is removed.

### For contributors

- CONTRIBUTING.md's map of the clone names every file and folder at
  the top of the repository but `.gitignore`: `tests/`, `changelog.d/`,
  `.github/`, `uv.lock`, `MANIFEST.in`, QUICKSTART.md,
  AI_CODING_GUIDE.md, PROJECT_SELECTION_GUIDE.md, CLAUDE.md and
  `.zenodo.json` join it, and `docs/WRITING.md` joins the documents
  under `docs/`. `tests/test_v0153_project_map.py` holds the map to the
  tree: every path it names must be one that git tracks, and each file
  or folder at the top must be in the map, or among those the test
  leaves out, each with its reason. The line for `occurrences.py` names
  the page for choosing occurrences, which the module builds.
- `scripts/check_promises.py` no longer lists `docs/history/` among
  the folders it leaves unread, and the tests that read or named the
  folder or the workflow guide follow.
  `tests/test_v0151_history_folder.py` now holds that the folder is
  gone and that NOTICE's addresses lead to the tag, and checks the tag
  in a clone that has it.
