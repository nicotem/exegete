### Documents

- **Claude's plans in the Terminal guide.** The guide names the Ultra
  plan beside Free, Pro and Max wherever it names Claude's personal
  plans, as Claude's pricing page lists them under "Individual" (read on
  19 November 2026). Claude Code's login is given as Pro, Max or Ultra,
  since the page offers Claude Code on every paid plan and not on Free.
- **An institution's account.** PRIVACY.md's rung 3 quotes Anthropic's
  pages, read on 19 November 2026. On a Team or Enterprise plan, the
  account's Primary Owner manages its data, and can request it through
  data exports, which may contain your conversations, the files you
  uploaded and usage patterns. On Enterprise, the Compliance API can
  pull chat data and file content, which your organisation's retention
  rules keep, indefinitely by default. Its reference for a chat's
  messages lists the results of the tools the chat used, and no page
  says whether those include what Exegete's tools return in Claude
  Desktop's chat. By Anthropic's documentation of that API, it also
  pulls the Claude Code and Cowork sessions run on your computer under
  the Enterprise account, with the text of what their tools returned,
  Exegete's included, kept six years by default. The Primary Owner
  switches that API on, or a parent
  organisation's Primary Owner for every organisation linked to it, and
  Owners can create keys for their own organisation. Before the Terminal
  guide's table suggests Claude Desktop's chat on such an account, it
  says that the extension is not signed, that a university or employer
  may block it, and that whoever manages the account can say whether it
  allows it; it now also says what the Primary Owner's exports and the
  Compliance API can reach. Its row on OpenAI's apps quotes OpenAI's
  page on enterprise privacy: on ChatGPT Business, workspace admins "can
  view, access, export, and delete end user conversations in the
  workspace", and on Enterprise and Edu they "can access an audit log of
  conversations and GPTs" (the Internet Archive's capture of 16 November
  2026).
- **Codex on mobile.** The Terminal guide and PRIVACY.md call OpenAI's
  phone route by the name OpenAI's pages give it, Codex on mobile, and
  suggest leaving the computer's remote access off for participants'
  data. The guide says that the ChatGPT app for iOS shows it as Codex,
  and an app that still uses the earlier label as Remote. OpenAI's Codex
  pricing page, read on 19 November 2026, lists "Mobile remote control"
  for the Plus, Pro, Business, Enterprise and Education plans, and not
  for an API key. By Codex's source at release 0.170.0, its command line
  can also switch remote access on, with the experimental
  `codex remote-control`. Remote access can then stay on after you quit
  Codex; after `codex remote-control start` it comes back with Codex's
  background server, even after `codex remote-control stop`, until
  `codex app-server daemon disable-remote-control` switches it off. The
  guide says so, and PRIVACY.md points to it.
- **What Codex keeps.** PRIVACY.md says, from Codex's source at release
  0.170.0, that Codex's log database also keeps the answers you give to
  Codex's own questions in Plan mode. It also says that Codex's command
  line starts a background server by default. That server keeps running
  after you quit Codex and writes to the same log database, and
  `codex app-server daemon stop` stops it before you delete those files.
  The Terminal guide's uninstall steps name those answers and that
  background server. Its "Updating" says, from the same source, that
  this background server ends a conversation, and Exegete with it, a
  little over a minute after you leave it. So after a session in Codex's
  command line, you could wait two minutes before updating, or stop that
  server.
- **OpenAI's privacy policy for Europe.** openai.com refuses automated
  reading, so PRIVACY.md quotes the policy from the Internet Archive's
  capture of 18 November 2026: what it says of training, of the content
  of business customers, and of how soon OpenAI removes what you delete.
- **The Terminal guide's training warning.** The guide's table and its
  first step for OpenAI's apps say what training means for
  participants' data, then which setting switches it off, as
  PRIVACY.md does. These passages, and PRIVACY.md's on what a deletion
  in Codex leaves, were read again as a researcher new to Exegete
  would read them, and their facts kept.
- **Training in Codex.** OpenAI's article on training changed on
  16 November 2026 (the Internet Archive's capture of 18 November). It
  no longer names Codex's "Include environments" setting, and says
  that with a personal ChatGPT account your ChatGPT training preference
  applies to your Codex conversations. The Terminal guide and
  PRIVACY.md now say so, where they suggested switching that setting
  off too.
- **Work Cloud.** The Terminal guide and PRIVACY.md gave the case of a
  Work conversation that reaches a connected computer as one for
  enterprise workspaces only. OpenAI's page on getting started with
  Work, read on 19 November 2026, speaks of any workspace that gives you
  Work Cloud and local computer access, so the guide now says that,
  citing that page. PRIVACY.md's warning that tool results do not stay
  on the connected computer now covers local computer access for Work
  Cloud or for dots, and quotes OpenAI's page on it: neither Work nor a
  dot "provides strict zero data retention", and for Work "deleting a
  conversation does not remove every related copy".
