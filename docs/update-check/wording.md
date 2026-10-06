# Keeping researchers up to date: wording

**Date:** 2026-10-04, updated 2026-10-06
**Version:** 4, the texts as built in nicotem/exegete#11 (commit 23404b9). Version 3 held the drafts, revised after five reviews, with the decisions of 5 October 2026 applied (no mailing list, no network-free reminders, GitHub Issues only for help; design section 1). Section A now gives the built texts, and ends with a short list of where they depart from the drafts, and why.
**Companion to:** design.md (the design), beside this file. "Design 3.5" means section 3.5 there; two of its sections are cited by name: "The decisions, D1 to D21" (section 12) and "To verify on a real computer" (section 13).
**Status:** section A holds the texts as they are in the code: A1 in packaging/desktop-extension/manifest.in.json, A2 as check_for_updates' docstring in src/exegete/server.py, A3 to A6 in src/exegete/updates.py. Sections B, C and D cover work not yet done: B and C are drafts (the "Install or update Exegete" page, whose screenshots need a real Mac and a real Windows computer, and the release notes' opening lines), and D records that nothing is planned outside the software for now. Section E records where each document change now lives. The texts of section A and the document changes of section E are in nicotem/exegete#11, which is not merged or released yet; the page of section B and the lines of section C are not built.

**Since the port onto 0.14.2 (6 October 2026):** this record describes pull request #11 as built at 23404b9. Ported onto 0.14.2 for its release, five things changed, and where this record says otherwise, the code and the CHANGELOG's 0.14.2 entry hold: (1) a copy started as `uvx qualcoder-mcp` is the uvx route, no longer the old name in a virtual environment (whose pip command could not work in uv's cache), and uvx under either name gets steps of its own: quit the app, name the version in its entry (`exegete@<version>`), open it again; (2) a one-time note goes first in an answer, not last, and only into an answer of at most 20,000 characters (`updates.NOTE_MAX_ANSWER`), since it counts as given once added; (3) `check_for_updates`' description puts its rules first (only when the user asks, the steps as returned, the steps left to the user), and the extension's answer no longer promises pictures, since the update page has none yet; (4) the counts and sizes are 0.14.2's: 75 tools in `full`, 22 in `core`, 76 in `lifecycle`; (5) README's "Keeping Exegete up to date" is folded into 0.14.2's paragraph on updating, and release.py carries 0.14.2's words. The Pages site's `latest.json` and update page are prepared, outside the repository, for the maintainer to publish at the release.

## How to read this document

**Placeholders.** In section A each quotation is the built text, word for word, with a placeholder wherever the code puts in a value. The built strings carry no Markdown, so a name such as EXEGETE_UPDATE_CHECK appears without code marks, as in the code. Steps are shown numbered; in the answer they are the items of the `steps` list, without numbers.

| Placeholder | Meaning |
|---|---|
| `<new>` | The newest version in display form, for example 0.15.0-alpha (the answer's `newest_version`) |
| `<new date>` | Its release date, from the version file, for example 12 November 2026 (`newest_released`) |
| `<installed>`, `<installed date>` | The same for the copy that is running. `<installed>` is "unknown" when the running version cannot be read. `<installed date>` is release.RELEASED (src/exegete/release.py), given only when the running version is release.VERSION; otherwise it and its parentheses are left out, and `installed_released` is null |
| `<new pip>` | The newest version in the form pip needs, for example 0.15.0a0 |
| `<first-check date>` | The earliest date of the first check: seven days after the disclosure was given, as the computer's own clock gives the date (updates.FIRST_CHECK_WAIT, _local_date) |
| `<page>` | The "Install or update Exegete" page, https://nicotem.github.io/exegete/update/ (updates.UPDATE_PAGE; the answer's `instructions_page` field). Not published yet: it comes with the GitHub Pages site (D3), planned for the release that adds the check (design section 9) |
| `<notes>` | The newest version's release notes, https://github.com/nicotem/exegete/releases/tag/v<new> (the answer's `release_notes`, given when a newer version exists) |
| `<installed notes>` | The same for the installed version (the after-update note, A6) |
| `<download>` | https://github.com/nicotem/exegete/releases/download/v<new>/exegete-<new>.mcpb (updates.download_link; the answer's `download_link`, for the extension only; until the CI jobs of D8 exist, the file is attached to each release by hand, under this name) |
| `<issues>` | GitHub Issues, the one place to ask for help (D14): https://github.com/nicotem/exegete/issues |
| `<python>` | The environment's Python (sys.executable), written for this computer's shell only: from the home folder as `$HOME/...` in Terminal (a Mac or Linux) or `$HOME\...` in PowerShell (Windows), or as its full path when it is outside the home folder. A path holding a quote (straight or curly), a backtick or `$`, or in Terminal `!` or `\`, or a character that is not printable or that forbidden_display_char flags, gets no command (updates.shell_path; design 3.6) |
| `<folder>` | The folder of a copy of the source, written as `<python>` is |
| `<install link>` | A constant link to a named section of INSTALL.md on GitHub: "Updating the MCP Server" (updates.INSTALL_UPDATING) or "Coming from qualcoder-mcp" (updates.INSTALL_COMING_FROM) |
| `<first version>` | The first version that has the check, for example 0.14.2-alpha |
| `<kind of error>` | A short plain name for the kind of failure, one of: "no connection", "no answer in time", "certificate not trusted", "the website refused", "the website redirected", "not the expected file", "the answer was too large", "address not allowed" |
| `<size>` | The file's size, for example 2.4 MB |
| `<summary>` | The installed version's summary, built into it: SUMMARY in src/exegete/release.py, given only when the running version is release.VERSION (design 3.5). It ends with its own full stop |

**Decisions these texts follow** (design, "The decisions, D1 to D21"):
- decided on 5 October 2026: D1 (c), on in the extension and off on the Terminal route; D2, off means Exegete itself makes no connection, the tool included; D3, Pages; D4, no reminders; D5, no check tool in `core`; D10 (a), no text from the network; D11, hosts ask before the check runs where they ask at all; D12, once per version; D14, GitHub Issues only;
- also decided on 5 October 2026: D19, keep the after-update note (A6); D20, keep the disclosure note (A4); D21, no QUAL-SOFTWARE posts for now.

If a decision changes, these passages change, and with them the code that holds them (src/exegete/updates.py; check_for_updates' docstring in src/exegete/server.py; packaging/desktop-extension/manifest.in.json) and the tests that pin them (tests/test_updates.py; for A1, tests/test_v014_desktop_extension.py):
- D1: A1, A3.9, A4, B, C, E1, E2, E3, E5, E6, E10
- D2: A1, A2, A3.9, B, E3, E6, E8, E10
- D3: `<page>`, E1, E3
- D5: A2, A4, A5, B, C, E6, E8, E10
- D10: A3.2, A3.3, A5, B, E3, E10
- D11: A2, B, E3, E6, E8, E10
- D12: A5, E10
- D19: A6, E3, E10
- D20: A3.11, A4, C, E3, E6, E10

**Conventions:**
- Versions appear in the project's display form (0.15.0-alpha), never the pip form, except inside commands.
- The register is the project's: plain, sober, British spelling, short sentences, no promises the code does not keep.
- **[to verify]** marks behaviour not yet seen on a real computer (design, "To verify on a real computer").
- Every text in src/exegete names the app "Claude Desktop" and the model "the assistant"; "Claude" alone appears only in A1 (the manifest) and in the drafts B and C.
- One set of terms throughout:
  - "stay as they are" for projects and settings;
  - "a minute or two";
  - "What's new";
  - "You have";
  - "the Terminal route";
  - "switch on/off": the control may be a checkbox or a toggle **[to verify]**.

---

## A. Text inside Exegete

A1 is in packaging/desktop-extension/manifest.in.json, A2 is the docstring of check_for_updates in src/exegete/server.py, and A3 to A6 are in src/exegete/updates.py (tool_answer, _extension_steps, _terminal_steps, _disclosure_text, _notice_text, _after_update_text).

**How the notes (A4 to A6) are delivered.** Each note is added to the next successful answer from another tool (a JSON object without an `error` field), as its last field, `exegete_notice`, so that it reaches the structured content too (design 3.5; server.py, _ExegeteMCP.call_tool; updates.attach). A refusal or an error carries none, and the note waits for the next answer; check_for_updates' own answers never carry one. An answer carries one note at most, in this order: the disclosure note (A4), then the after-update note (A6), then the new-version notice (A5). No note is given when Exegete cannot tell which version it is (for example, a copy of the source that was not installed).

### A1. The setting in the extension

Built in packaging/desktop-extension/manifest.in.json as `user_config.update_check`, word for word as below: type boolean, default true, not required. The manifest's `env` passes it to the server as EXEGETE_UPDATE_CHECK (`"${user_config.update_check}"`) and sets EXEGETE_INSTALLED_AS to `extension`; its `privacy_policies` list PRIVACY.md, "Checking for new versions", and GitHub's general privacy statement.

**Title:** Tell me when a new version is out

**Description:**
> Exegete fetches a small file from its website, which GitHub hosts, to see whether a newer version exists: once a week at most on its own, and when Claude checks for you. Claude then tells you once. Nothing from your projects is sent; GitHub records your computer's internet address and the time, as any website does. Switch this off and Exegete itself makes no connection.

*Note:* how much of the description Claude Desktop's settings screen shows is **[to verify]**.

### A2. The tool's description (read by the assistant only)

Built as the docstring of check_for_updates in src/exegete/server.py, word for word as below. The tool takes no arguments. It is async, and runs updates.tool_answer in a worker thread. Its annotations are TOOL_CHECKS_ONLINE: not read-only, not destructive, idempotent and open-world; it is the only open-world tool. It is in the `full` and `lifecycle` tool sets, not in `core` (D5).

> Check whether a newer version of Exegete exists, and say how to install it. Use when the user asks whether Exegete is up to date, how to update it, or which version they have. Returns the installed version and its date, the newest version and its date, numbered steps for this computer, and links. Give the user the message and the steps. Do not suggest other ways to update, such as GitHub's Releases page. When checking is switched off in Exegete's settings, it makes no connection and returns the installed version and where to look.

### A3. The tool's answers (`message` and `steps`)

Built in src/exegete/updates.py, tool_answer. The answer is JSON with `message`, `steps` (a list, empty when there is nothing to do), `installed_version`, `installed_released`, `installed_as` (the route in words, updates.ROUTE_WORDS), `checking` ("on" or "off"), `newest_version`, `newest_released`, `important`, `up_to_date`, `download_link` (the extension only), `release_notes` (when a newer version exists) and `instructions_page` (always `<page>`). Commands and quitting steps are given for this computer's own system only: PowerShell on Windows, Terminal otherwise. No `exegete_notice` is ever added to this tool's answer. Asked twice within a day, it fetches once: an attempt made in the last day, asked or weekly, is not repeated, and its result, a failure included, is given again. Only one fetch runs at a time: an asked check waits for one already running, and uses its result.

**A3.1 Up to date**
> You have the newest version of Exegete, <installed> (<installed date>). Exegete will tell you here when a newer one comes out.

**A3.2 Newer version, Claude Desktop extension**

Message:
> A newer version of Exegete is available: <new> (<new date>). You have <installed>, which keeps working, so there is no hurry. What's new, and pictures of each step: <page>. Your projects stay as they are, and so do your conversations. After Claude Desktop reopens, the assistant may need to open your project again.

For a release marked important, the second sentence becomes:
> It fixes a problem that could affect your projects: the page below says what it is, and what to do until you update.

On every route the important release's second sentence is this one. On the old-name route with no command (A3.6), the message then names no page, only INSTALL.md's section; the update page is only in `instructions_page`.

Steps:
1. Click this link to download the new version: <download>. When it has finished, your browser shows the file in its list of downloads. Its name starts with exegete-<new>.
2. Click the file there, or double-click it in your Downloads folder. Claude Desktop opens and shows Exegete, with the same reminder as the first time to install only extensions you trust. Click Install. If Claude Desktop says it needs to fetch a few things, click Install again: it takes a minute and needs the internet. If nothing happens, or another program opens the file, open Claude Desktop's Settings, then Extensions, then Advanced settings, click Install Extension..., and choose the file.
3. Quit Claude Desktop completely, then open it again, so that it starts the new version. Closing its window is not enough. On a Mac: with Claude Desktop in front, press Cmd and Q together, or choose Quit from the app's menu at the top of the screen. Wait until the Claude Desktop icon has gone, then open the app again. If you are not sure it has quit, restarting the computer always works.

   On Windows the middle sentence is instead: "On Windows: at the bottom right of the screen, near the clock, find the Claude Desktop icon (you may need to click the small upward arrow first), right-click it and choose Quit (or Exit)." On Linux, step 3 gives the Mac sentence.

Quit or Exit, and the time quitting takes, are still to check on a real computer (design, "To verify on a real computer", item 5), and so is whether Exegete's settings survive an update (item 6); the message says nothing about the settings.

Not built: Exegete cannot tell whether an organisation manages Claude Desktop's extensions, so no answer says so. The update page's troubleshooting (section B) covers a managed computer.

**A3.3 Newer version, pip in a virtual environment**

Message:
> A newer version of Exegete is available: <new> (<new date>). You have <installed>, which keeps working, so there is no hurry. What's new: <page>.

Steps:
1. Quit the app that started Exegete (for example Claude Desktop, Claude Code or LM Studio), so that nothing is using it while it changes.
2. `In Terminal, run: "<python>" -m pip install "exegete==<new pip>"` on a Mac or Linux; on Windows, `In PowerShell, run: & "<python>" -m pip install "exegete==<new pip>"`.
3. Open the app again.

When no safe path can be written for `<python>`, there are no steps and the message is A3.7's.

**A3.4 Newer version, pipx or uv tool**

Message and steps 1 and 3 as A3.3. Step 2 (with "In PowerShell" on Windows):
- pipx: `In Terminal, run: pipx install --force "exegete==<new pip>"`
- uv tool: `In Terminal, run: uv tool install --force "exegete==<new pip>"`

These commands hold no path, so they are always given.

INSTALL.md, "Updating the MCP Server", says that `uv tool upgrade exegete` keeps a version pinned this way, and to run the steps again with the newer version (added on 6 October 2026). The pipx form is still untried on a real computer.

**A3.5 Newer version, a copy of the source**

Message: as A3.3. A copy of the source is an editable install whose folder holds `.git` (updates._source_folder). A git copy started under the old name gets these steps too, with no old-name paragraph. When the folder or `<python>` cannot be written safely, there are no steps and the message is A3.7's.

Steps:
1. As A3.3.
2. On a Mac or Linux: `In Terminal, go to the copy's folder (cd "<folder>"), then run git fetch --tags, then git merge --ff-only v<new> (it stays on its branch, and refuses if the copy has changes of its own), then "<python>" -m pip install -e .`

   On Windows: `In PowerShell, go to the copy's folder (cd "<folder>"), then run git fetch --tags, then git merge --ff-only v<new> (it stays on its branch, and refuses if the copy has changes of its own), then & "<python>" -m pip install -e .`
3. Open the app again.

**A3.6 Newer version, started under the old name (qualcoder-mcp)**

Steps are given only in a virtual environment that is not a uv tool or pipx one, with a safe `<python>`, and when the newest version is below 1.0: as A3.3, with step 2 `In Terminal, run: "<python>" -m pip install "qualcoder-mcp==<new pip>" "exegete==<new pip>"` (on Windows, `In PowerShell, run: & "<python>" -m pip install "qualcoder-mcp==<new pip>" "exegete==<new pip>"`). The message is A3.3's, followed by:
> qualcoder-mcp is Exegete's earlier name. Its last release comes with Exegete 1.0, and its earlier setting names are read only until then, so move to the new name before 1.0: INSTALL.md, "Coming from qualcoder-mcp", has the steps: <install link>.

Otherwise there are no steps, and the message is:
> A newer version of Exegete is available: <new> (<new date>). You have <installed>, which keeps working, so there is no hurry. This copy was started under Exegete's earlier name, qualcoder-mcp. INSTALL.md, "Coming from qualcoder-mcp", shows how to move to the new name and update: <install link>.

(For an important release the second sentence is A3.2's important one.) This covers a copy under uv tool or pipx (the two-name forms are untried, so no command is given), one outside a virtual environment, one whose `<python>` cannot be written safely, and every copy once the newest version is 1.0 or later (design section 10). A copy started as `uvx qualcoder-mcp` is taken for a virtual environment and gets the pip command for uvx's own cache; the build does not yet tell it apart.

The untried forms, as version 3 drafted them, are kept here for when they are tried on a real computer: for uv tool, `uv tool install --force "qualcoder-mcp==<new pip>" --with "exegete==<new pip>"`; for pipx, `pipx install --force "qualcoder-mcp==<new pip>"`, then `pipx runpip qualcoder-mcp install "exegete==<new pip>"` **[to verify]**.

**A3.7 Exegete cannot tell how it was installed, or cannot write a safe command (uvx, anything unrecognised, or pip or a copy of the source whose path no command can carry safely)**
> A newer version of Exegete is available: <new> (<new date>). You have <installed>, which keeps working, so there is no hurry. How to update depends on how Exegete was installed: <page> shows the way for Claude Desktop, and INSTALL.md, "Updating the MCP Server", the Terminal route: <install link>.

(For an important release, the second sentence is A3.2's important one.)

**A3.8 Could not check**
> Exegete could not reach its website to check for a newer version (<kind of error>). The computer may be offline, or the network may block it. This does not affect anything else Exegete does. You have <installed> (<installed date>). You can look yourself at <page>.

**A3.9 Checking switched off**
> Checking for new versions is switched off, so Exegete made no connection. You have <installed> (<installed date>). You can look yourself at <page>.

In the extension, the message ends:
> To let Exegete check, open Claude Desktop's Settings, then Extensions, then Exegete, and switch on "Tell me when a new version is out".

On the Terminal route, the message ends:
> To let Exegete check, set EXEGETE_UPDATE_CHECK to on in the settings of the app that starts it (INSTALL.md, "Environment variables the server reads").

**A3.10 This copy is newer than the newest published version**
> You have <installed>, which is newer than the newest published version, <new>. There is nothing to update.

**A3.11 Before the first check** (the disclosure's waiting period)
> Exegete's first check for new versions will be on <first-check date>, as it says when this version is first used; until then it makes no connection. You have <installed> (<installed date>). You can look yourself at <page>.

When no disclosure is recorded on this computer yet (`disclosed_at`; for example, when this tool is asked before any other tool has answered successfully since a start with checking on), the answer begins with the disclosure itself, said to the researcher, followed by the text above:
> This version of Exegete can tell you when a new version is out. Once a week at most, and when you ask, it fetches a small file from its website, which GitHub hosts. Nothing from your projects is sent; GitHub records your computer's internet address and the time. To switch it off: Claude Desktop's Settings, then Extensions, then Exegete, "Tell me when a new version is out".

On the Terminal route the last sentence is: "To switch it off, set EXEGETE_UPDATE_CHECK to off in the settings of the app that starts Exegete." The disclosure note (A4) is then recorded as given, and not repeated.

**A3.12 No answer yet**
> Exegete has no answer from its website yet. You have <installed> (<installed date>). You can look yourself at <page>.

Given when Exegete holds neither a result nor a failure (for example, a first check that has not finished in time).

**A3.13 The running version cannot be read** (checking on)
> Exegete cannot tell which version this is (it is running from a copy that was not installed), so it cannot compare it with the newest. See <page>.

With checking off, such a copy gets A3.9, which then reads "You have unknown."

### A4. The disclosure note (once per computer, in the first successful answer after a start with checking on)

> Note for the user, who sees it only if you pass it on. Pass it on once, briefly, after answering their request. This version of Exegete can tell them when a new version is out. Once a week at most, and when they ask, it fetches a small file from its website, which GitHub hosts. Nothing from their projects is sent; GitHub records their computer's internet address and the time. It is switched on, and its first check will be on or after <first-check date>. To switch it off before then or at any time: Claude Desktop's Settings, then Extensions, then Exegete, "Tell me when a new version is out". PRIVACY.md, "Checking for new versions", says exactly what is sent.

Nothing is given at the start itself. The note is added to the first successful answer from a tool other than check_for_updates after a start with checking on, when no disclosure is recorded on this computer. A refusal or an error carries no note; the note waits for the next answer. The record (`disclosed_at` in update_check.json) is shared by every copy of Exegete on the computer, so a later version does not give the note again. If the state file cannot be written, only this run's memory keeps the record, so a later start may give it again.

On the Terminal route, where the check is off unless switched on, that is the first answer after someone switches it on, unless another copy of Exegete on the same computer (the extension, for example) has already given it. On every route other than the extension, the second-to-last sentence reads "To switch it off before then or at any time, set EXEGETE_UPDATE_CHECK to off in the settings of the app that starts Exegete." In the `core` tool set, which has no check tool, the words "and when they ask" are left out: "Once a week at most it fetches a small file ...".

**If check_for_updates comes first.** When checking is on and check_for_updates is called before the disclosure has been given on this computer, its `message` opens with the disclosure, said to the researcher (A3.11). The disclosure is then recorded as given, and no note follows in a later answer.

### A5. The new-version notice (once per new version on this computer, while checking is on)

> Note for the user, who sees it only if you pass it on. Pass it on once, in one or two sentences, after answering their request. Do not check for updates or start updating unless they ask. A newer version of Exegete is available: <new> (<new date>). They have <installed>, which keeps working, so there is no hurry. What's new: <page>. To update, they can ask: "How do I update Exegete?"

**For a release marked important:**
> Note for the user, who sees it only if you pass it on. Pass it on calmly, once, after answering their request, and before making any further change to a project. An important update to Exegete is available: <new> (<new date>). It fixes a problem that could affect projects. They have <installed>. <page> says what the problem is and what to do until they update. To update, they can ask: "How do I update Exegete?"

**In the `core` tool set,** "To update, they can ask: ..." becomes "To update, see <page>" (the notice then ends without a full stop).

It is given while checking is on, when the newest version found is newer than the one running and has not yet been announced on this computer; every copy of Exegete there shares that record (the 20 most recent versions announced, updates.ANNOUNCED_KEEP). An answer from check_for_updates that names a newer version counts as telling, so no notice for that version follows.

No notice can be given until the GitHub Pages site is published (planned, outside nicotem/exegete#11), since a notice needs latest.json from that site, which will also hold `<page>`.

### A6. After an update (once per update on this computer, no network, whether checking is on or off)

> Note for the user, who sees it only if you pass it on. Pass it on once, briefly, after answering their request: Exegete has been updated to <installed> on this computer, so the update worked. What's new: <summary> The full notes: <installed notes>.

`<summary>` is release.SUMMARY in src/exegete/release.py and ends with its own full stop. When the version running is not the one release.py describes (release.VERSION), the "What's new" sentence is left out.

It is given when the version running is newer than the newest version recorded as having run on this computer (`highest_version_run`). It is not given on a new installation or after a downgrade. The record is raised only once the note has been given, so a restart before any answer keeps it due. After an update from 0.14.1 or earlier (which kept no such record), it is given only with checking off; with checking on, the disclosure note takes its place.

### Where the built texts depart from the drafts

Version 3's drafts were built with these changes. Where no reason is recorded in a commit or a code comment, the list says so.

- **"Claude Desktop" and "the assistant".** Every text in src/exegete names the app "Claude Desktop" and the model "the assistant", where the drafts said "Claude". tests/test_v0141_intro_openai.py (TestServedTextsAreHostNeutral.test_no_source_file_addresses_claude) refuses "Claude" in the package's source unless "Desktop" or "Code" follows, which also rules out the draft's Mac step ("click Claude in the menu bar"). A1 lives in the manifest, outside that rule, and still says "Claude".
- **One system only.** Commands and the quitting step are given for this computer's own system (PowerShell on Windows, Terminal otherwise), not in both forms. No reason is recorded; the server knows its own system, and A2 promises "numbered steps for this computer".
- **The page's field is `instructions_page`**, not the design's `update_page`. No reason is recorded. The likely one: tests/test_v014_server_wide.py reads a word such as update_page (TOOL_SHAPED) as the name of a tool that does not exist, unless NOT_TOOLS lists it.
- **The extension's answer (A3.2).** Step 1 no longer says where the downloads list usually is; step 2 holds its fallback; step 3 gives "Quit (or Exit)" on Windows and no waiting time; the closing lines end the message, without "Exegete's settings stay as they are". No reason is recorded; the open questions stay on the design's list ("To verify on a real computer", items 5 and 6). The line for organisations that manage Claude Desktop's extensions is not built, since Exegete cannot tell.
- **Terminal step 1** is one fixed sentence: the app that started Exegete is not detected.
- **The git steps** use `git merge --ff-only v<new>` in place of `git checkout v<new>`, so the copy stays on its branch and a copy with changes of its own is refused (a review finding, commit 1448475).
- **The old name (A3.6).** Only a plain virtual environment, before 1.0, gets the two-name pip command. Under uv tool or pipx no command is given, since the two-name forms were never tried (the comment in updates._terminal_steps), and from 1.0 there are no steps. A git copy started under the old name gets the git steps (commit 1448475). A copy started with uvx under the old name is not yet told apart.
- **How the route is found.** updates.detect_route checks the extension's mark only (the extension-folder fallback of D16 is not built; no reason is recorded), then a git copy, the old name, uv tool, pipx, uvx and pip. Its docstring gave the design's order until 6 October 2026.
- **A3.7** keeps A3.2's second sentence, and also serves pip or a git copy whose path no command can carry safely. **A3.8** says "the network" for "your university's network". **A3.11** is in the present tense. No reasons are recorded.
- **The disclosure in the tool's own answer** (A3.11). The hook never adds a note to check_for_updates' answers ("check_for_updates says these things itself", server.py, _ExegeteMCP.call_tool), so the tool gives the disclosure itself before it states the first-check date.
- **Dates and the summary.** `<installed date>`, and A6's "What's new" sentence, appear only for the version release.py describes: release.py holds the words of one release, and nothing about a version is read from the network (D10).
- **Three answers with no draft:** A3.12, A3.13, and A3.6's message for an old-name copy that gets no command ("This copy was started under Exegete's earlier name, qualcoder-mcp. ...").
- **When the notes are given.** Nothing is written at a start. The disclosure rides on the first successful answer and is recorded once per computer; the after-update note is recorded only once given, so a restart before any answer keeps it due (commit 1448475). When the state file cannot be written, a copy in memory keeps the weekly limit and the "once" for the rest of the run (commit 1448475); a later start may then repeat a note.

---

## B. The "Install or update Exegete" page

Written for someone who has never used GitHub. It needs screenshots from a real Mac and a real Windows computer, each with alt text and a written equivalent. It loads nothing from other sites.

**Not built yet.** The Pages site, its latest.json and this page are planned outside nicotem/exegete#11; the screenshots need a real Mac and a real Windows computer. Exegete already gives the page's address, https://nicotem.github.io/exegete/update/ (updates.UPDATE_PAGE): in every new-version notice (in `core`, "To update, see <page>"), and in every answer of check_for_updates (the field `instructions_page`, and most messages), which sends here the copies it can give no command for (uvx, an install it cannot recognise, a folder name no quoting can carry). The extension's answer (A3.2) promises "pictures of each step" here. README.md, "Keeping Exegete up to date", links it too. So the page must be live before the first release that carries the check.

> # Install or update Exegete
>
> The newest version is **<new>**, from <new date>.
>
> **What's new:** <two or three plain sentences>. *(For an important release: what the problem is, whether it can have affected your projects and how to tell, and what to avoid until you update.)*
>
> **[ Download Exegete <new> for Claude Desktop (exegete-<new>.mcpb, <size>) ]**
>
> Every version before 1.0 is marked "alpha", meaning an early version. The newest alpha is the one to use.
>
> Not sure which version you have? Ask Claude: "Is Exegete up to date?" (Exegete <first version> or later; not with the extension's "Tool set" `core`, which has no such tool). It answers even with the check switched off, without connecting to anything.
>
> ## In Claude Desktop
>
> Your projects stay as they are, and so do Exegete's settings **[to verify]**. It takes a minute or two.
>
> 1. **Download.** Click the button above. When it has finished, your browser shows the file in its list of downloads. Its name starts with exegete-<new>.
>    *[screenshot: the browser's download list, Mac and Windows]*
> 2. **Open it.** Click the file in that list, or double-click it in your Downloads folder. Claude opens and shows Exegete, with its usual reminder to install only extensions you trust. Click **Install**. If Claude says it needs to fetch a few things, click **Install** again: this needs the internet and can take a minute.
>    *[screenshot: Claude's installation screen]*
> 3. **Restart Claude.** Quit Claude completely and open it again. Closing the window is not enough.
>    - Mac: click **Claude** in the menu bar at the top of the screen, then **Quit Claude**.
>    - Windows: right-click the Claude icon near the clock, at the bottom right (you may need to click the small upward arrow first), then **Quit** **[to verify]**.
>    - Wait until the Claude icon has gone, then open Claude again.
>    *[screenshot: the menu, Mac and Windows]*
> 4. **Check.** In a new conversation, ask Claude: "Is Exegete up to date?". If Claude asks whether it may use Exegete, allow it. It should answer that you have <new>.
>
> Use Exegete on more than one computer? Update it on each one.
>
> ## Something went wrong?
>
> - **Nothing happens when I open the file, or another program opens it.** In Claude, open Settings, then Extensions, then Advanced settings, click **Install Extension...**, and choose the file.
> - **There are several Exegete files in my Downloads folder.** Use the one with <new> in its name. A name ending in (1) or (2) is the same file downloaded twice, and either works. You can delete the older ones **[to verify]**.
> - **My browser asks whether to keep the file.** Choose Keep **[to verify on a managed Windows computer]**.
> - **Claude says "This extension isn't signed..." or "Desktop extensions ... are disabled on this device".** Your university or employer manages this computer or your Claude account. Send this page to your IT team, with PRIVACY.md, which says what Exegete does and sends: the decision is theirs. The version you have keeps working meanwhile.
> - **Exegete's tools are missing, or the old version still answers.** Claude was not fully quit. Quit it as in step 3, wait, and open it again; or restart the computer.
> - **Anything else:** ask on GitHub Issues: <issues>. You need a free GitHub account (an email address and a password, like any website). Say what you did and what Claude showed; never include participants' data.
>
> ## Hear about new versions
>
> In Claude Desktop, unless you switched it off, Exegete checks once a week at most, and after it finds a new version, Claude tells you once, the next time it uses Exegete (if Claude passes the note on). If your network blocks the check, Exegete cannot tell you. You can also come back to this page at any time: it always shows the newest version.
>
> ## If you installed Exegete with a Terminal
>
> If you have switched Exegete's check on (`EXEGETE_UPDATE_CHECK=on`, from Exegete <first version>), ask your assistant "How do I update Exegete?" (not in the `core` tool set, which has no such tool). From Exegete's first check on, at least seven days after it first tells you about the check, the answer gives the command for this computer when it can: for pip in a virtual environment, pipx, uv tool or a copy of the source. Otherwise it points to this page or to INSTALL.md. If the check is off, follow INSTALL.md, "Updating the MCP Server": <install link>.
>
> *This site has no analytics, counters or cookies, and loads nothing from other sites.*

*Note:* the tool's own steps (A3.2) word the restart differently ("Claude Desktop" throughout, Cmd and Q first on a Mac, "Quit (or Exit)" on Windows). When the page is written, the two should agree.

---

## C. Release notes: the opening lines

From the release that first carries the check, every release note is to open with the lines below (not done yet: they are written when each release is prepared, design 4.5, step 3):

> **Do I need this update?** <one or two plain sentences: who benefits, and whether anything is urgent>
>
> **How to update:** in Claude Desktop, follow <page> (a minute or two; your projects stay as they are). You do not need to download anything from this page. If you installed with a Terminal: follow INSTALL.md, "Updating the MCP Server": <install link>; or, if you have switched Exegete's check on (from Exegete <first version>; not in the `core` tool set), ask your assistant "How do I update Exegete?": it gives the steps from its first check on, at least seven days after it first tells you about the check.


For the release that first adds the check, this paragraph comes first:

> **New: Exegete can tell you when a new version is out.** In the Claude Desktop extension, once a week at most, and when you ask, it fetches a small file from its website, which GitHub hosts. Nothing from your projects is sent; GitHub records your computer's internet address and the time. Claude tells you about it the first time it uses Exegete after the update (if Claude passes the note on), and Exegete makes its first check at least seven days after that, so you can switch it off first: Claude Desktop's Settings, Extensions, Exegete, "Tell me when a new version is out". If another copy of Exegete on this computer has already told you, it is not repeated, and the seven days count from then. On the Terminal route it is off unless you switch it on. If your ethics approval, consent wording or data-management plan describes what Exegete connects to, read PRIVACY.md, "Checking for new versions".

---

## D. Outside the software

Nothing, for now: the JISCMail list was dropped, and QUAL-SOFTWARE posts are set aside (design 5, D21).

---

## E. Changes to the project's documents

Every change drafted here is in the repository, committed in nicotem/exegete#11 (at 23404b9). Each item names the file and heading where the text now lives, and notes only where the committed words differ materially from the draft; the documents hold the full text. Design 6.2 lists every location.

### E1. README.md, "Other assistants" and "Keeping Exegete up to date"

The heading "### Other assistants, and updates" was split in two. "### Other assistants" keeps its first paragraph as it was, with its bold lead "**Other assistants.**". A new "### Keeping Exegete up to date" follows: an opening paragraph, three bullets, and the "**Updating.**" paragraph, moved and rewritten.

Differences from the draft:
- The "**Updating.**" paragraph keeps its bold lead and the sentence "An update never touches your projects."
- The switch-off path is "Claude Desktop's Settings, Extensions, Exegete".
- "Ask at any time" says "Ask "Is Exegete up to date?"", without "Claude", and adds "(from its first check on, a week after it first tells you about the check)" after "the newest one" (commit 1448475).
- The third bullet says "restart Claude Desktop", and the page "shows each step", with no promise of pictures. The page is not published yet (section B).

The sentence that tests/test_v0141_intro_openai.py (test_updating_covers_the_terminal_route) pins is kept word for word. Only one test boundary changed: TestTheStepsANewcomerCanGetWrong.test_a_first_session_speaks_to_any_assistant now ends at "### Other assistants". The "**Updating.**" lead was kept, so the "README, other assistants" span in _claude_code_routes ("**Other assistants.**" to "**Updating.**") is unchanged, and now also takes in the new subsection.

Also in README.md, "Claude Desktop, with one click": "the extension's two settings" is now "three settings".

### E2. README.md, "Where your data goes", the start of its first paragraph

It replaced "Exegete runs on your computer, has no online service of its own and sends nothing anywhere itself." Committed as drafted, except that the closing reference to PRIVACY.md is a link.

### E3. PRIVACY.md, a new section "Checking for new versions"

A new top-level section after "Your governance options, from default to fully local (Experimental)", so after rung 4 and "Cross-rung cautions", and before "OpenAI's apps: the ChatGPT desktop app and Codex (Experimental)". Its paragraphs: "What it does", "When it is on", "What it sends", "What this project receives", "What it keeps", "What enters the conversation", "Switching it off".

Differences from the draft:
- **What it sends:** both GitHub pages were read on 5 October 2026 through GitHub's own source for its documentation (github/docs), since docs.github.com could not be opened where this was written. The privacy statement's effective date (April 27, 2026) is given, and three passages are quoted: the controller, the data collected about interactions, and transfers. None is quoted on retention. The paragraph adds "The linked pages govern."
- **What this project receives** is only "Nothing: the site has no counter, analytics or log of this project's own." The draft's clause that GitHub shows the owner no record of who fetched the file is left out: that is still to check (design, "To verify on a real computer", item 11). The site is not published yet.
- **What it keeps** follows the state file's keys (updates._serialise): the last attempt and, if it failed, the kind of failure; the newest version found; the versions already told; the disclosure time and the first-check date; and the newest version run, kept even with checking off. It keeps no time of the last success and no dates for the notices (commit 1448475).
- **What enters the conversation** writes folders from `$HOME`, not `~`, since `~` does not expand inside double quotes (the comment above updates.shell_path).

*Corrected on 6 October 2026:* "When it is on" said "At its first start, Exegete tells you about the check through the assistant", and "What enters the conversation" said "(at the first start)". As built, nothing is given at a start: the disclosure goes with the first successful answer after a start with checking on, while no disclosure is recorded on this computer (A4). They now say "The first time the assistant uses Exegete with the check on, Exegete tells you about the check through the assistant" and "(the first time Exegete is used)". "What enters the conversation" also says now that a folder outside the home folder is written in full.

*Note:* still to do before the release: open the two live GitHub pages and check the quoted words against them, since PRIVACY.md's discipline note (in "Your governance options, from default to fully local (Experimental)") quotes official pages verbatim, with their URLs, and says the linked pages govern.

### E4. PRIVACY.md, "How your data flows", the opening paragraph

In place of "and nothing in this server ever "phones home"". Committed as drafted.

### E5. PRIVACY.md, other passages
- **"How your data flows", the paragraph "What leaves your machine through this server":** as drafted.
- **"How your data flows", "What stays local, always", the bullet on the server's own folder:** adds `update_check.json`. Committed with "when Exegete last checked" and a closing pointer, "; "Checking for new versions" says more". It lists less than "What it keeps" (not the kind of failure, the disclosure or the first-check date).
- **"Rung 4: fully local models (Experimental)", first paragraph:** as drafted, with "("Checking for new versions", below)" at the end of the first sentence.
- **The same paragraph, on verifying offline operation:** as drafted.

### E6. INSTALL.md
- **"Claude Desktop: the one-click extension (recommended)", step 4**, now "Look at its three settings", has a third bullet, "Tell me when a new version is out". Committed with "the first time the assistant uses Exegete it is told to say so" in place of "tells you the first time Claude uses Exegete (if Claude passes the note on)", and with a link to PRIVACY.md.
- **"Environment variables the server reads":**
  - the introduction now says that the extension sets both spellings of "these three settings", and that "The two settings of the check for new versions, below, are new and have one spelling only" (names.NEW_ONLY_SETTINGS, kept apart from names.SETTINGS);
  - `EXEGETE_TOOLSET`: `full` registers 74 tools and `lifecycle` 75;
  - a new item, `EXEGETE_UPDATE_CHECK`, after `EXEGETE_ALLOW_UNKNOWN_SCHEMA`. It has no version marker (the first version with the check is not fixed yet), and adds the once-a-day limit when asked, "in any letter case", that unset means on in the extension, and that the log says at every start whether checking is on;
  - a last item, `EXEGETE_INSTALLED_AS`, with no version marker, naming its value (`extension`). The mark has a second effect: with it, checking is on by default (updates.detect_route reads it as the extension route, and updates.read_setting defaults to on only for that route). Since 6 October 2026 the item says so: "It also makes checking on by default, as the extension's setting is."
- **"LM Studio (fully local) (Experimental)":** Step 3 now says 74 tools and about 196,000 characters, "measured under Python 3.13 with mcp 1.30.0, in an environment built from `uv.lock`". Step 5's entry ends its `env` with `"EXEGETE_UPDATE_CHECK": "off"`; the explaining sentence is in the paragraph after the block, after the sentence on a source (git) install: "The last line keeps Exegete's check for new versions off; it is off when unset too, and writing it down documents it." Step 7 is as drafted, with "its log says so at every start" added. "What to expect" is as drafted.
- **"ChatGPT's desktop app and Codex (Experimental)":** about 199,000 characters with `lifecycle`.
- **"What hosts do with the tools' read and write marks", first paragraph:** the `openWorldHint` sentence as drafted. PRIVACY.md cites this section for why the assistant normally asks before the check. Since 6 October 2026 a paragraph after the one on read_pseudonym_list says that check_for_updates is not marked read-only either, since it records each check, so a host that asks before a tool runs asks before it.
- **"Updating the MCP Server", first paragraph:** as drafted, with a sentence for the Terminal route: "On the Terminal route the check is off unless you set `EXEGETE_UPDATE_CHECK` to `on` ("Environment variables the server reads")." With the `core` tool set, check_for_updates is not registered, so asking gives no steps; the notice links the update page instead (design 3.5). Since 6 October 2026 the paragraph says so, after "for the steps": "(with the `lifecycle` or `full` tool set; with `core`, which has no check tool, the notice links the update page)". The PyPI block is followed by a sentence on a pinned `uv tool` install (A3.4).
- **"Uninstalling", step 3:** now lists "the record of the check for new versions (`update_check.json`: ...)". Since 6 October 2026 the list matches PRIVACY.md's "What it keeps": it adds the kind of failure, when it told you about the check, the date of its first check, and that the record is kept even with checking off.
- **Not changed:** "two settings" in the Codex recipe and in "Coming from qualcoder-mcp", which design 6.2 listed. Both are still true: the Codex entry sets two settings, and the qualcoder-mcp extension being updated had two.

### E7. The extension's long description (packaging/desktop-extension/manifest.in.json, `long_description`)

The sentence on the check follows "...PRIVACY.md)" as drafted. The last paragraph now reads: "The settings choose the tool set (with or without creating new projects), the folder where new projects and working copies are kept, and whether Exegete tells you when a new version is out."

The manifest also sets `EXEGETE_UPDATE_CHECK` to `${user_config.update_check}` and `EXEGETE_INSTALLED_AS` to `extension` in `server.mcp_config.env`, adds the setting `update_check` to `user_config` (A1), and lists two `privacy_policies` (D6): PRIVACY.md, "Checking for new versions", and GitHub's privacy statement. `build_manifest` in scripts/build_desktop_extension.py copies the new key.

### E8. TOOLS.md
- **"Data Safety", "General Safety", first bullet:** as drafted; the sentence goes on as before ("..., but tool results enter the conversation and are transmitted to whichever AI provider your host uses").
- **"Available Tools":** a new group, "Keeping Exegete up to date", with the entry for `check_for_updates()` (not drafted here): what it returns, that it is the only tool that reaches beyond this computer (at most once a day, and not at all when switched off), that it is not marked read-only since it records the check, so hosts ask before it runs where they ask at all, and that it is in `full` and `lifecycle`, not `core`. The counts are now 74 (`full`) and 75 (`lifecycle`), and the sizes about 196,000 characters (`full`, "Measured for this release ... under Python 3.13 with mcp 1.30.0") and about 199,000, roughly 50k tokens (`lifecycle`).

### E9. CONTRIBUTING.md
- **"Review before merge":** as drafted, with "(the version file of the check for new versions)".
- **"Style rules", "Disclosure is existence-only":** as drafted.
- **A new section, "The check for new versions"** (between "The earlier name" and "Licence"; commit 1448475), not drafted here: the address is permanent because no redirect is followed, so the account, the repository and its Pages site are never renamed or deleted, and no custom domain is set; the file keeps `"format": 1`; and each release updates src/exegete/release.py with pyproject.toml and the CHANGELOG heading, which tests hold together. Its first words were "Every installed copy fetches", which overstated, since only a copy with checking on fetches; since 6 October 2026 they read "Every installed copy with checking on fetches".

### E10. CHANGELOG.md, "[Unreleased]" (as committed in nicotem/exegete#11, not yet released)

The entry has an opening paragraph, "### Added: the check for new versions" with five bullets, "### Changed" with four, and "### Measured". Differences from the draft:
- "New versions announced in the conversation" says the note rides on the first successful tool answer, as its last field (`exegete_notice`); it gives the address, says the request is identified only as "Exegete", and says every failure (no answer within eight seconds included) ends as "could not check" with one log line naming the kind of failure only.
- A new bullet, "Told before anything connects", takes the draft's sentences on the setting, the disclosure and the seven-day wait, and says "Switched off, Exegete makes no connection, not even when asked."
- `check_for_updates` is "not marked read-only, since it records the check, so hosts ask before it runs where they ask at all; it is not in `core`", in place of the draft's "so hosts ask before it runs" (D11).
- "A note after an update" replaces the draft's one-time notes for checking off or failing, which D4 removed.
- A new bullet, "Two settings with one spelling only".
- "### Changed" adds the manifest's privacy policies; README's new section, with the matching sentences of PRIVACY.md and INSTALL.md and QUICKSTART's quit-first order; and the test suite's refusal of any name lookup or connection beyond this computer.
- The draft's line on attaching the extension to each release twice is not in the entry: D8's CI jobs are not built yet.
- "### Measured" gives the figures: full 195,975, core 64,804 and lifecycle 198,554 characters on Python 3.13.14 with mcp 1.30.0, in an environment built from `uv.lock`; 205,683, 68,096 and 208,402 on Python 3.11.15; the tool adds 709 characters to `full` and `lifecycle`, and none to `core`.

"On the Terminal route `EXEGETE_UPDATE_CHECK` is off unless set" was loose, since `off`, `false`, `0` and an unrecognised value all keep it off (updates.read_setting); since 6 October 2026 it reads "is off unless set to `on`", as PRIVACY.md and INSTALL.md put it.

### E11. QUICKSTART.md, "Updating Later"

Not drafted here (design 6.2 lists it). It now says to quit the client fully first, so that no copy of the server is running while its files change, then to run `git pull` and `venv/bin/pip install -e .`, and then to open the client again.
