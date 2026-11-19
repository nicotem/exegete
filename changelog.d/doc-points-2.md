### Documents

- **Local models and LM Link.** Where the Terminal guide's LM Studio
  recipe, its step 7 and PRIVACY.md's checklist say that a local model
  keeps the data on your computer, they now add that LM Studio's LM
  Link, in preview, can load the model on another computer, which then
  reads the conversation (read on 19 November 2026). The recipe
  suggests checking in LM Studio where the model is loaded, or leaving
  LM Link off. Its step 4 says in plain words that at 16k the core
  set's schema would not fit, and that for the full tool set, `full`,
  you could set 64k.
- **What a bug report can publish.** The bug report form counts coder
  names, yours, the AI coder name and colleagues', among what the
  tools' answers hold.
- **The reading folder.** INSTALL.md's list of what stays after an
  uninstall gives the pages for checking an import's letters and for
  choosing occurrences of a name, beside the reading pages and the
  copies of originals.
- **The notes Exegete gives once.** PRIVACY.md gives every case in which
  one can come again: two copies of Exegete on one computer, a file
  Exegete could not write, a stop in the instant after the answer has
  gone out, and, for the notes that the check exists and that a newer
  version is out, a check you asked for that is still running.
- **Claude's plans.** PRIVACY.md's rung 1 takes in Claude Code signed
  in with Pro, Max or Ultra, as Claude's pricing page, read on 19
  November 2026, offers Claude Code on the paid plans and not on Free.
- **An institution's account.** Before the Terminal guide's recipe for
  an API key suggests Claude Desktop's chat on a Team or Enterprise
  account, it says that the extension is not signed and may be
  blocked. PRIVACY.md's rung 3 and the guide's table say that the
  Compliance API keeps the transcripts of local sessions six years by
  default, while chats and files follow the organisation's retention
  rules, indefinitely by default. They add that no page says whether a
  chat's copy holds what Exegete's tools returned, though the API's
  reference lists the results of the tools a chat used (Anthropic's
  pages, read on 19 November 2026). Rung 3 quotes in full what a
  Primary Owner's exports may contain: "your conversations with Claude,
  uploaded files, and usage patterns."
- **Codex.**
  - The guide says that Codex's command line starts its background
    server when you open Codex, by default. So remote access switched
    on with `codex remote-control start` is back as soon as you open
    Codex again, even after `codex remote-control stop` (Codex's source
    at release 0.170.0).
  - Where the guide's uninstall steps and PRIVACY.md name Plan mode,
    they say what it is: the mode in which Codex proposes a plan before
    it starts work (OpenAI's page on its commands, read on 19 November
    2026).
  - The guide says in plain words how much of a tool's answer Codex
    passes on to a model, and what that means for a file read in parts
    with a model Codex does not list.
  - PRIVACY.md says what a dot is, one of OpenAI's always-on agents,
    which some personal Pro accounts have too; what one given your
    computer can do; and that Revoke access withdraws it (OpenAI's
    pages, read on 19 November 2026).
- **Backups a prune could not remove.** Where PRIVACY.md says what
  work cut short leaves, and where it offers `prune_backups` to remove
  a file's copies, it now says that what is left of a backup the prune
  could not remove whole stays under a hidden name, until a later
  backup removes what it can of it.
- **Exegete, and QualCoder if you use it.** PRIVACY.md calls an older
  copy of Exegete by Exegete's name, and says "if you use QualCoder"
  where it spoke of that program's files and actions as if you did.

### For contributors

- `tests/test_v0151_facts.py` holds the hour after which a later
  backup removes a backup's hidden folder,
  `database.BACKUP_LEFTOVER_SECONDS`, wherever PRIVACY.md, a fragment
  or the prune's note states it, a time in words read in seconds.
- The tests that held the words of the LM Studio recipe's step 4, of
  PRIVACY.md's account of the earlier name and of the reading folder's
  tidying hold their facts instead. The tests of two safety facts on
  Codex's remote access hold their sense, so that each fails with its
  fact reversed.
