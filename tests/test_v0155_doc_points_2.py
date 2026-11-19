# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.5, the documents' points left this week (row 17 of the sprint of
17 November 2026): the new facts the documents state, each held to the
code or to the page it rests on. Pins of a sentence's words moved to
their facts in their own files; the backups' hour is a fact of the
facts check (tests/test_v0151_facts.py).

- INSTALL's list of what stays after an uninstall names the four kinds
  of file the reading folder holds (reading_folder.py);
- the API-key recipe warns of the unsigned extension before it suggests
  Claude Desktop's chat;
- where the guide and PRIVACY.md say that a local model keeps the data
  on the computer, they say what LM Studio's LM Link changes;
- PRIVACY.md gives the four cases in which a note Exegete gives once
  comes again, the fourth for the two notes check_for_updates tells
  itself (updates.py, server.py);
- the prune's remains, under a backup's hidden name, where PRIVACY.md
  says what work cut short leaves and how to remove a file's copies, and
  that the next backup removes what it can of them, the rest being the
  researcher's to delete (sweep_partial_backups clears no marks);
- rung 1 gives Claude Code to the paid plans alone; rung 3 and the
  guide's row give the retention of chats and of local sessions apart,
  and say that no page settles whether a chat's copy holds what
  Exegete's tools returned; Plan mode, dots and the background server
  are explained where they are named.
"""

import inspect
import os
import re
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exegete import database, reading_folder, server, updates  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GUIDE = "docs/installing-from-the-terminal.md"


def _flat(name: str) -> str:
    return " ".join((REPO / name).read_text(encoding="utf-8").split())


def _between(text: str, start: str, end: str) -> str:
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def test_the_uninstall_names_what_the_reading_folder_holds():
    """The reading folder holds four kinds of file (reading_folder.py's
    account of itself): reading pages with a file's whole text and its
    codings, read-only copies of originals, the import's pages for
    checking letters (previews_folder) and the pages for choosing
    occurrences of a name (occurrences_folder). Each holds a file's
    text, and INSTALL's item on what stays names all four."""
    account = reading_folder.__doc__
    for kind in ("reading copies", "read-only copies of originals",
                 "preview pages", "pages for choosing occurrences"):
        assert kind in account, kind
    assert callable(reading_folder.previews_folder)
    assert callable(reading_folder.occurrences_folder)
    item = _between(_flat("INSTALL.md"), "- **The reading folder**",
                    "- **Claude Desktop's log of the extension**")
    # (the readability reading: what the two pages are for, in the words
    # of reading_folder.py's account, and a sentence for what they hold)
    for kind in ("a file's whole text and its codings",
                 "read-only copies of originals",
                 "checking letters that look garbled before an import",
                 "choosing occurrences of a name to leave as they are"):
        assert kind in item, kind
    # (the fix round: what the two pages hold, the text, and for the page
    # for choosing, which words are the names to replace, which is why it
    # goes after an hour; after an uninstall no tidy runs)
    assert "marks which words are names" in " ".join(account.split())
    start = item.index("It also holds the pages")
    pages = item[start:item.index("It is ", start)]
    assert "a file's text" in pages
    assert re.search(r"page for choosing marks[^.]*names you asked to "
                     r"replace", pages)
    assert "after an uninstall it stays until you delete it" in item


def test_the_api_key_recipe_warns_before_it_suggests_the_chat():
    """The recipe for Claude Code with an API key suggests Claude
    Desktop's chat on a Team or Enterprise account, as the table's row
    and PRIVACY.md's rung 3 do: like them, it first says that the
    extension is not signed and may be blocked (INSTALL.md, "Installing
    the extension"; scripts/build_desktop_extension.py does not sign)."""
    build = (REPO / "scripts/build_desktop_extension.py").read_text(
        encoding="utf-8")
    assert "Signing is not done here." in build
    guide = _flat(GUIDE)
    recipe = _between(guide, "## Claude Code with an Anthropic API key",
                      "**1. Install Exegete**")
    # (the readability reading: the extension named as Claude Desktop's)
    warning = recipe.index("Exegete's extension for Claude Desktop is not "
                           "signed, and an institution may block it (the "
                           "table above)")
    assert warning < recipe.index("this project suggests Claude Desktop's "
                                  "chat")
    row = _between((REPO / GUIDE).read_text(encoding="utf-8"),
                   "| **Anthropic commercial-terms routes**", "\n")
    assert "may block unsigned extensions, or extensions altogether" in row


READ_ON = r"read on \d{1,2} [A-Z][a-z]+ 20\d\d"


def _recipe() -> str:
    guide = _flat(GUIDE)
    return _between(guide, "## LM Studio (fully local)",
                    "## ChatGPT's desktop app and Codex")


def test_where_a_local_model_keeps_the_data_lm_link_is_named():
    """The LM Studio recipe's opening, its step 7 and PRIVACY.md's
    checklist say that a local model keeps the data on the computer; each
    now says that LM Studio's LM Link can load the model on another
    computer (lmstudio.ai/link, read on 19 November 2026), and the
    recipe gives the row's suggestion."""
    recipe = _recipe()
    opening = recipe[:recipe.index("**Step 1.")]
    claim = opening.index("stay on your computer")
    assert "unless LM Studio's LM Link" in opening[
        claim:opening.index(".", claim)]
    assert re.search(r"<https://lmstudio\.ai/link>, " + READ_ON, opening)
    assert ("You could check in LM Studio where the model is loaded, or "
            "leave LM Link off.") in opening
    assert "participants' data included" in opening
    step = _between(recipe, "**Step 7.", "**What to expect.**")
    # (the fix round: the exception reaches the conversation the model
    # reads, not the model alone, as the opening and rung 4 say)
    (local,) = [sentence for sentence in step.split(". ")
                if "local" in sentence and "LM Link" in sentence]
    assert local.index("conversation") < local.index("unless LM Link")
    assert "the chats" not in local
    checklist = _between(_flat("PRIVACY.md"), "- **Which assistant, and "
                         "whether it opens files by itself.**",
                         "- **What stays on the computer")
    # (the readability reading: LM Link named as LM Studio's, and what it
    # loads elsewhere, the model)
    assert re.search(r"A local model keeps the data on your computer, "
                     r"unless LM Studio's LM Link loads the model on "
                     r"another computer \(\"Rung 4\"\)", checklist)


def test_every_case_in_which_a_note_given_once_comes_again():
    """A note given once is recorded per run (_Run.given) and in the state
    file once its answer is out (mark_given; standard_output.py), so it
    comes again with two copies of Exegete, a file it cannot write, or a
    stop just after the answer. check_for_updates tells the disclosure
    and a newer version itself, given once its worker returns, while
    other answers can carry them meanwhile; it never carries a note due,
    and never tells the note after an update."""
    told = inspect.getsource(updates.tool_answer)
    assert 'Note("disclosure"' in told and "new version:" in told
    assert "after update" not in told
    calls = inspect.getsource(server.ExegeteMCP.call_tool) \
        if hasattr(server, "ExegeteMCP") else inspect.getsource(server)
    assert "tool.name == updates.TOOL_NAME" in calls
    worker = inspect.getsource(server.check_for_updates)
    assert "updates.give(note, request_id)" in worker
    note = _between(_flat("PRIVACY.md"), "**What enters the conversation.**",
                    "**Switching it off.**")
    for case in ("when two copies of Exegete run on the same computer",
                 "when Exegete cannot write its file",
                 "when Exegete stops in the instant after the answer has "
                 "gone out",
                 "The first two notes can also come twice while a check "
                 "you asked for runs."):
        assert case in note, case
    assert note.index("that the check exists") < note.index(
        "that a newer version is out") < note.index("that an update worked")


def test_what_a_prune_that_stopped_leaves_is_said_where_copies_are():
    """remove_backup_folder renames a backup to the hidden name of a
    backup being made before it removes it, so what a removal or a
    process stopped partway leaves stays under that name; a backup whose
    rename was refused stays whole, listed, under its own name. The next
    backup's sweep removes what it can of such a folder once
    BACKUP_LEFTOVER_SECONDS have passed (the facts check holds the hour):
    it passes every error over and clears no marks, so what stopped the
    prune can stop it too, and the rest is the researcher's to delete.
    PRIVACY.md says so where it says what work cut short leaves, and
    points there where it offers prune_backups."""
    assert "_partial_backup_name(stem, timestamp)" in inspect.getsource(
        database.remove_backup_folder)
    sweep = inspect.getsource(database.sweep_partial_backups)
    assert "ignore_errors=True" in sweep
    assert "_clear_backup_marks" not in sweep
    privacy = _flat("PRIVACY.md")
    cut_short = _between(privacy, "Work cut short can leave copies behind.",
                         "A save of the names list cut short")
    # (the fix round: the remains of a removal that stopped, not of a
    # refused rename; what they can hold, not what they must)
    assert re.search(r"what is left of [^.]*`prune_backups` [^.]*stopped "
                     r"partway", cut_short)
    assert re.search(r"\bcan\b[^.]*names file[^.]*`pseudonyms\.json`",
                     cut_short)
    assert "among them" not in cut_short
    (sweeping,) = [sentence for sentence in cut_short.split(". ")
                   if "next backup" in sentence]
    assert "what it can" in sweeping and "yours to delete" in sweeping
    narrow = _between(privacy, "Some ways narrow that reach",
                      "## What pseudonymisation is for")
    assert re.search(r"`prune_backups` [^.]*stopped partway[^.]*hidden name "
                     r"\(above\)", narrow)
    entry = _between(_flat("changelog.d/doc-points-2.md"),
                     "**Backups a prune could not remove.**", "- **")
    assert "removes what it can" in entry and "yours to delete" in entry


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0,
                    reason="a folder's mode stops a removal on Linux and "
                    "macOS, for an account other than the administrator's")
def test_the_next_backup_leaves_what_a_mark_keeps(tmp_path):
    """What PRIVACY.md now says of a hidden folder (the fix round, the
    readers' major): a later backup's sweep removes what it can of it
    and passes over the rest. A hidden folder over an hour old, with a
    folder in it not writable for its owner, keeps that folder and the
    file inside it; one without such a mark goes."""
    stem = "Study"
    project = tmp_path / f"{stem}.qda"
    project.mkdir()
    kept = tmp_path / f".{stem}_backup_20200101_000000_partial_0123abcd.qda"
    gone = tmp_path / f".{stem}_backup_20200101_000001_partial_4567cdef.qda"
    for folder in (kept, gone):
        (folder / "inner").mkdir(parents=True)
        (folder / "inner" / "pseudonyms.json").write_text(
            "{}", encoding="utf-8")
        (folder / "data.qda").write_text("", encoding="utf-8")
    marked = kept / "inner"
    os.chmod(marked, stat.S_IRUSR | stat.S_IXUSR)
    try:
        assert database.is_partial_backup_name(kept.name, stem)
        assert database.sweep_partial_backups(project) == 1
        assert not gone.exists()
        assert (marked / "pseudonyms.json").exists()
        assert not (kept / "data.qda").exists()
    finally:
        os.chmod(marked, stat.S_IRWXU)


def test_rung_one_gives_claude_code_to_the_paid_plans_alone():
    """Claude's pricing page, read on 19 November 2026, gives Claude Code
    "No" on Free and "Yes" on Pro, Max and Ultra."""
    privacy = (REPO / "PRIVACY.md").read_text(encoding="utf-8")
    (heading,) = [line for line in privacy.splitlines()
                  if line.startswith("### Rung 1:")]
    assert "Free, Pro, Max and Ultra" in heading
    assert re.search(r"Claude Code signed in with Pro, Max or Ultra\)$",
                     heading)
    assert "signed in with them" not in heading
    rung = _between(_flat("PRIVACY.md"), "### Rung 1:", "### Rung 2:")
    # (the fix round: the page quoted, as the rungs say they quote it)
    assert re.search(r"<https://claude\.com/pricing>, " + READ_ON
                     + r"[^.]*\"Claude Code is included in all paid "
                     r"plans\.\"", rung)


def test_who_can_reach_an_institution_s_chats_and_for_how_long():
    """Anthropic's pages, read on 19 November 2026: a Primary Owner's
    exports may contain "your conversations with Claude, uploaded files,
    and usage patterns" (9265372); the Compliance API keeps the local
    sessions' transcripts, tool results included, six years by default
    (compliance-sessions.md 132), while chats and files follow the
    organisation's retention rules, "indefinite by default"
    (compliance-faq.md 63); its reference for a chat's messages lists the
    tools' results ("Text content returned by the tool"), and no page
    says whether a Claude Desktop extension's are among them."""
    rung = _between(_flat("PRIVACY.md"), "### Rung 3:", "### Rung 4:")
    assert ("which may contain your conversations with Claude, uploaded "
            "files, and usage patterns.\"") in rung
    for page in ("manage-claude/compliance-faq",
                 "api/compliance/apps/chats/messages/list"):
        assert ("<https://platform.claude.com/docs/en/" + page + ">") in rung
    assert re.search(r"messages/list>, both " + READ_ON, rung)
    assert ("\"the retention rules configured for your organization "
            "(indefinite by default)\"") in rung
    # (the fix round: the reference quoted, never "each tool's result")
    assert re.search(r"chat's messages [^.]*\"Text content returned by the "
                     r"tool\"", rung)
    assert "each tool's result" not in rung
    # (the readability reading: "these" named, a chat's tool results; the
    # fix round: the fact, that no page settles it)
    assert re.search(r"No page says whether [^.]*what Exegete's tools "
                     r"return in Claude Desktop's chat\.", rung)
    sessions = rung.index("\"stored for 6 years from capture by default\"")
    assert rung.index("Cowork sessions run on your computer") < sessions \
        < rung.index("chats and files follow")
    row = _between((REPO / GUIDE).read_text(encoding="utf-8"),
                   "| **Anthropic commercial-terms routes**", "\n")
    assert "the files you uploaded" in row
    chats = row.index("can pull your chats and files")
    assert row.index("(indefinitely by default)", chats) < row.index(
        "is not documented", chats) < row.index("kept six years by default")
    # (the readability reading: the six years in a sentence of their own,
    # whose subject is those transcripts)
    assert re.search(r"transcripts of the Claude Code and Cowork sessions "
                     r"[^.]*\. Those transcripts [^.]*kept six years by "
                     r"default", row)
    fragment = _flat("changelog.d/plans-and-readings.md")
    assert "the files you uploaded" in fragment
    assert "indefinitely by default" in fragment


def test_plan_mode_is_explained_where_it_is_named():
    """OpenAI's page on slash commands, read on 19 November 2026:
    `/plan` switches to plan mode, to "Ask Codex to propose an execution
    plan before implementation work starts." Its questions are Plan
    mode's (Codex's source at rust-v0.170.0)."""
    guide = _between(_flat(GUIDE), "3. **Look at what the hosts keep.**",
                     "4. **Exegete's own folder")
    assert re.search(r"in Plan mode, where it proposes a plan before it "
                     r"starts work \(<https://learn\.chatgpt\.com/docs/cli/"
                     r"slash-commands>, " + READ_ON, guide)
    privacy = _flat("PRIVACY.md")
    assert re.search(r"in Plan mode, where Codex proposes a plan before it "
                     r"starts work \(the page on its commands, above, "
                     + READ_ON, privacy)
    above = privacy[:privacy.index("where Codex proposes a plan")]
    assert "<https://learn.chatgpt.com/docs/cli/slash-commands>" in above[
        above.rindex("**Codex keeps session transcripts"):]


def test_dots_are_explained_with_what_they_can_do_and_how_to_stop_them():
    """OpenAI's pages, read on 19 November 2026: a dot is "an always-on
    agent", rolling out to eligible Pro accounts too (docs/dots.md); one
    given a computer can "Create local Work or Codex threads and control
    existing local Codex threads.", and Revoke access removes that grant
    (enterprise/cloud-local-access.md 30, 205); "Neither experience
    provides strict zero data retention" (118)."""
    phones = _between(_flat("PRIVACY.md"),
                      "**Phones, through a connected computer.**",
                      "**Services for individuals.**")
    # (the readability reading: what a dot is, a sentence of its own; the
    # fix round: the fact, not the words)
    assert re.search(r"A dot is [^.]*always-on agent", phones)
    assert "personal Pro accounts" in phones
    # (the fix round: the page on local computer access quoted on
    # withdrawing a dot's access, enterprise/cloud-local-access.md 205)
    assert ("\"Choose Revoke access and confirm to remove the dot's grant "
            "for that computer.\"") in phones
    assert re.search(r"<https://learn\.chatgpt\.com/docs/dots>, " + READ_ON,
                     phones)
    assert ("\"Create local Work or Codex threads and control existing "
            "local Codex threads.\"") in phones
    assert "Revoke access" in phones
    assert "neither Work nor a dot \"provides strict zero data retention\"" \
        in phones
    assert "neither feature" not in phones
    assert "Where your workspace gives you local computer access, for" \
        not in phones
    case = _between(_flat(GUIDE), "There is one more case",
                    "- **ChatGPT on a phone**")
    # (the fix round: the pointer, whatever its words)
    assert re.search(r"PRIVACY\.md, \"OpenAI's apps\"[^.]*\bretention\b",
                     case)
