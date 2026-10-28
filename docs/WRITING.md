# Writing guide

Exegete is a qualitative analysis application that a researcher uses in
conversation with an AI assistant. The assistant works Exegete through
named actions, called tools; Exegete answers each one, and sometimes
refuses with a reason. This guide is for anyone who writes for Exegete:
the documents in this repository, the settings and pages a researcher
sees on screen, and the texts the assistant receives.

## Who reads these texts

- **Researchers.** They are qualitative researchers, and most are not
  programmers. They need to know what Exegete does for their study,
  what happens to their data, and what to do next. Where a step can be
  done with clicks, describe that route. Send a reader to a terminal
  window, to a file edited by hand or to a hidden folder only when
  there is no other way.
- **The assistant.** It reads a description of each tool, and the
  notes and refusals in Exegete's answers. It needs to know what a tool
  does, when to use it and what to ask the researcher. It often repeats
  our words to the researcher, so those words must also read well to a
  person.
- **Contributors.** They need each rule with its reason, so that the
  next change keeps it. The rules below each give theirs.

## The voice

Write as one person explaining something to another, in words you would
use aloud. Say what Exegete does now. Leave out praise such as powerful,
seamless or easy, and leave out quips, jokes, exclamation marks, emoji
and marketing language, because a reader deciding about their
participants' data needs facts. Do not rank Exegete against other
programs. Do not patronise: calling something easy talks down to the
reader. Write in UK English. Use a full stop or a comma rather than a
dash, so that each sentence keeps one idea.

A text for a researcher informs and warns, then leaves the decision to
them. Say what could go wrong and what they could do instead, then
stop. Give the facts and the risks, and leave the choice to the
researcher. Never reassure in place of informing: instead of "your data
is safe", say where the data goes and who can read it there. Texts for
the assistant are different: they give firm instructions, such as never
to open the project's folder directly, because a change made that way
skips Exegete's checks and backups.

## Plain sentences

- Put one idea in each sentence, and begin with its subject and verb. A
  sentence of more than about thirty words usually holds two ideas.
- Make a person, a company or a program the subject, because a reader
  wants to know who does what. "Your AI provider sets the terms" is
  clearer than "The terms attach to the account".
- Say what something is. Say what it is not only when the reader needs
  to know it.
- Use a heading rather than a fragment before a colon. "What changed"
  as a heading reads better than "Less visible:" at the start of a
  paragraph.
- Prefer ordinary words to technical ones, and explain a technical word
  the first time each document uses it, because each document may be
  the first one a reader opens.
- Leave out words that only mean something inside this project.
- Turn a chain of possessives into a sentence with a verb: "the overlap
  that QualCoder's report counts", not "QualCoder's report's overlap".
- Give an aside its own sentence, or cut it, because an aside makes the
  reader hold the main clause for longer.
- State the case rather than ask a rhetorical question, which makes the
  reader answer before they have learnt anything.
- Do not write in capitals for emphasis, because they make every rule
  look equally urgent. Say plainly what matters and when it applies.
- Give each heading the name of what its section covers, with a
  capital only for the first word and for names.
- Tell a fact once and point to it from elsewhere, so that a correction
  is made in one place. Keep a warning in every document a researcher
  may read on its own.
- Keep a setting's description within about forty-five words, because
  the settings page shows little of a longer one. Say what the setting
  does and its default, and name any other setting by its title.
- Read the text aloud, and rewrite wherever you stumble.

## Promises and numbers

Describe what is built, in the present tense. Name a planned feature
with its planned release, never "soon" or "coming". For what is
missing, write "Exegete does not do this" and point to the roadmap for
plans. Do not promise how long a step will take: that depends on the
reader's computer, the project and the AI provider.

Date every claim about another program, or about a provider's terms and
prices, with the day it was checked. Give rounded counts and sizes in
prose and leave exact figures to a table, unless the reader acts on one,
such as a time limit. A script writes the exact size of everything the
assistant receives from Exegete into `docs/snapshot/`, in characters.
The size matters because each text uses part of what the assistant can
take in at once. The documents give rounded figures and point there.

## Words we use

Use one word for one thing, in every text. A coding is a code attached
to a passage of a document, and each coding carries the name of the
coder who made it.

| We write | For | Rather than |
|---|---|---|
| Exegete | the application, wherever a text says what it is or does. Use "the server" only where the text is about how an app starts Exegete, as in an app's settings or log. | this tool, an add-on, a plug-in, a connector |
| you; the researcher | the person whose study it is. Documents for researchers say "you"; texts the assistant receives say "the researcher". | the user |
| the assistant; the AI provider | the AI the researcher talks to through an app such as Claude Desktop or LM Studio, and the company that runs the model, when it does not run on the researcher's own computer | Claude for every assistant; the model or the LLM in the documents |
| your project | what Exegete creates, reads and changes. It is kept in the file format of QualCoder, a free qualitative analysis program. "Study" means the research itself. | |
| the names list; the names file | the real names with the pseudonyms that replace them, and `Names to replace.txt`, which the researcher fills in outside the conversation so that the list never passes through the conversation | the mapping, the key |
| replacing names; pseudonymisation | what Exegete does with the names list. It reduces risk; it makes no one anonymous. | anonymisation |
| backup | the copy Exegete takes before it changes a project's database, kept beside the project | safety net |
| your coder name; the AI coder name | the two names that keep the researcher's own codings apart from those approved from the assistant's suggestions, so that their origin stays visible | |
| the assistant suggests | the division of work. The assistant suggests, the researcher decides, and Exegete records what was approved. | Exegete suggests, AI-coded segments |
| your codebook, coding and counts | what an export holds | results, findings |

## How texts are checked

Automatic checks run on every change. They test the links, and they
check the counts, folders and versions in the documents against the
code. They look for exclamation marks, marketing words and the other
habits named above, and they report each document's sentence lengths
and reading grade. Before a release, read the texts a new reader meets
first as a whole, as a researcher new to Exegete would read them. Those
texts are the README's opening, the quick start guide, the settings
page of the Claude Desktop extension, the update page and Exegete's
first answers in a conversation.
Whoever changes PRIVACY.md, or any statement about what reaches the AI
provider, checks it against the code.
