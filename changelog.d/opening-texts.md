### Changed

- **The desktop extension's description and its six settings are
  rewritten**: each setting says what it does and its default, within
  about forty-five words, and refers to any other setting by its title.
- **What the assistant is told first says what QualCoder is.** The
  opening text and the brief describe the project as kept in the format
  of QualCoder, "a free qualitative analysis program". The opening text
  now says documents, where it said documents and transcripts. The
  opening text is 2,042 characters, within the 2,048 that Claude Code
  kept before its version 2.1.296, and the full brief about 13,700. The
  brief now says that the backup comes before every change to the
  project's database, and that setting the AI coder name and preparing
  the names file take none. Where `select_project`'s answer tells the
  assistant to ask or check, it says "the researcher".

### Documents

- **README.md is plainer and a little shorter**: 629 lines, from 678,
  in the voice of the writing guide. It mentions QualCoder only where a
  sentence is about QualCoder or offers it as a choice, explains "the AI
  provider" once, and gives its warnings as what could happen and what you could
  do. It says that the desktop extension works on Claude's Free plan, as
  Claude's pricing page listed it on 28 October 2026, and presents a
  local model as a route to consider for particular uses. The
  drawings, the table of the two programs, the groups of tools and the
  map stay, rewritten. The map names the new documents. Claude Code's
  figures are in the guide to installing from the Terminal. Before that guide's steps for
  OpenAI's apps it gives the training switch, and where it sends Claude
  Code's users it says that Claude Code opens files by itself.
- **QUICKSTART.md** is rewritten in the same voice, within 250 lines.
- **The update page** is rewritten in the same voice, and says that on
  Python 3.10 the steps cannot install a version after 0.15.1-alpha.1.
- **The writing guide**, `docs/WRITING.md`, says who reads Exegete's
  texts and how to write them; CONTRIBUTING.md's style rules point to
  it.

### For contributors

- The tests that held the old sentences of these texts now hold the
  new ones or test the facts behind them, and the tests that compared a
  released entry's figures with today's sizes read those figures as
  history. The texts check's ledger holds no seeded line for README.md,
  QUICKSTART.md, the update page or the extension's manifest.
