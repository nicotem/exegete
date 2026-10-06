# SPDX-License-Identifier: LGPL-3.0-or-later
"""What the document import says, in plain words (0.14.3, provisional).

Every refusal and warning the import gives is one of these fixed texts
with numbers, never a library's message or a document's own words: a
hostile document can put instructions in an archive entry's name or a
PDF object's, and an error message would carry them. Each warning says
what the researcher will see, what to do, and why.
"""

from typing import Any, Dict, Sequence

COPY_A_PATH = (
    "To copy a file's or folder's place: on a Mac, select it in Finder, "
    "hold Option, right-click and choose Copy as Pathname; on Windows 11, "
    "right-click it and choose Copy as path. Then paste it.")

SAME_READING = ("QualCoder reads the file the same way, so both programs "
                "agree on every coding.")

PATH_REFUSALS = {
    "missing": "There is no file or folder at this place on your "
               "computer. " + COPY_A_PATH,
    "relative": "This is not a full path. Give the place from the top of "
                "the disk (for example /Users/you/Documents/Interviews or "
                "C:\\Users\\you\\Documents\\Interviews), or starting with ~ "
                "for your home folder. " + COPY_A_PATH,
    "network": "This is a network path (\\\\server\\share or //server/"
               "share). Exegete does not open those, because reaching one "
               "makes Windows offer your account's sign-in to the computer "
               "it names. Use the drive letter your computer has given that "
               "share (for example H:), or a share mounted in Finder; "
               "copying the files to your computer is the other way, and if "
               "they are participant data, check your study's data plan "
               "first.",
    "link": "This place is reached through a link (a shortcut, symbolic "
            "link or junction). Exegete follows a link only into a cloud "
            "drive's own folder. Give the place the link points to.",
    "hidden": "This is a hidden file, or is in a hidden folder. Exegete "
              "does not import from hidden places. Move the files to an "
              "ordinary folder, such as one in Documents, and ask again.",
    "macos_permission": "macOS has not let the assistant's app open this "
                        "place. In System Settings, Privacy & Security, "
                        "Files and Folders, allow that app to open it "
                        "(Documents, Desktop or Downloads), then ask "
                        "again.",
    "permission": "Your account cannot open this place. Check its "
                  "permissions, or copy the files to a folder of your own.",
    "unreadable": "This place could not be read.",
    "not_a_file": "This is neither an ordinary file nor a folder.",
    "project": "This is inside the open project's own folder. Bring "
               "documents in from where you keep them, not from the "
               "project.",
    "state_folder": "This is inside Exegete's own state folder, which "
                    "holds no documents.",
    "reading_folder": "This is inside Exegete's reading folder, which "
                      "holds reading copies, not documents to import.",
}

OTHER_FORMATS = {
    ".doc": "This is an older Word document. Open it in Word and save it "
            "as a Word document (.docx), then import that.",
    ".pages": "This is a Pages document. In Pages, choose File, Export To, "
              "Word, then import the .docx.",
    ".gdoc": "This is a shortcut to a Google document, not a document. In "
             "Google Docs, choose File, Download, Microsoft Word, then "
             "import the .docx.",
    ".docm": "This is a Word document with macros. Open it in Word and "
             "save it as a Word document (.docx), then import that.",
    ".rtfd": "This is a TextEdit document with pictures. In TextEdit, "
             "choose File, Save, and the format Word 2007 (.docx).",
}
KNOWN_OTHER_SUFFIXES = tuple(OTHER_FORMATS)

FILE_REFUSALS = {
    "unsupported": "Exegete does not import this kind of file (it imports "
                   ".docx, .odt, .rtf, .txt, .md, .html, .htm, .srt, .vtt, "
                   "and .pdf and .epub with the optional part).",
    "optional_missing": "This computer's Exegete cannot read PDF and EPUB "
                        "files yet: they need an optional part. QualCoder "
                        "can import them.",
    "too_large": "This file is larger than Exegete reads for this kind of "
                 "document ({limit_mb} MB). QualCoder has no such limit "
                 "and would import it.",
    "name_in_use": "The project already has a file with this name, with "
                   "other contents. Rename the file on your computer, then "
                   "ask again.",
    "same_name_in_batch": "Another file in this batch has the same name "
                          "(letter case aside). Rename one of them on your "
                          "computer, then ask again.",
    "online_only": "This file is kept online only. Open it once on this "
                   "computer, then try again.",
    "changed_while_read": "This file changed while it was being read. Try "
                          "again once it is saved.",
    "not_an_archive": "This file's contents do not match its name: it is "
                      "not a {format} file Exegete can read.",
    "not_this_format": "This file's contents do not match its name: it is "
                       "not a {format} file Exegete can read.",
    "archive_too_many_entries": "This file holds more parts than Exegete "
                                "reads ({limit}). QualCoder has no such "
                                "limit.",
    "archive_part_too_large": "Unpacked, part of this file is larger than "
                              "Exegete reads ({limit_mb} MB). QualCoder "
                              "has no such limit.",
    "archive_too_large": "Unpacked, this file is larger than Exegete reads "
                         "({limit_mb} MB). QualCoder has no such limit.",
    "damaged": "This file is damaged or could not be read.",
    "xml_entities": "This file declares XML entities, which ordinary "
                    "documents do not use and attacks do, so Exegete does "
                    "not read it (QualCoder imports it). Open it in its own "
                    "app and save a fresh copy.",
    "no_text": "No text was found in this file. QualCoder would store the "
               "file's own codes as its text, which is noise; Exegete does "
               "not import it.",
    "empty": "This file is empty.",
    "pdf_password": "This PDF is protected by a password. Save a copy "
                    "without the password (in Preview or Acrobat), then "
                    "import that.",
    "unstorable": "This file holds a character a project cannot store "
                  "(QualCoder's import fails on it too). Open it in its "
                  "own app and save a fresh copy.",
    "unstorable_rtf": "It holds half of a character RTF writes in two "
                      "halves (an emoji, say) without the other half, which "
                      "a project cannot store (QualCoder's import fails on "
                      "it too). Save it as Word (.docx) in its app, or "
                      "remove that character, then import that.",
    "too_long": "Its text is {characters} characters long, over Exegete's "
                "limit of {limit}. Import long books and reports in "
                "QualCoder.",
    "reader_timeout": "Reading this file took longer than {seconds} "
                      "seconds, so it was stopped.",
    "reader_memory": "Reading this file needed more memory than Exegete "
                     "allows ({limit_mb} MB), so it was stopped.",
    "reader_failed": "This file could not be read.",
    "not_supported": "Exegete does not import this kind of file.",
}

# Saving a copy as UTF-8, in the apps researchers have: what a hold of a
# file that is not UTF-8 suggests (the owner's decision of 6 October
# 2026: no guessing, and plain steps instead).
_WHY_NOT_UTF8 = (
    "so it is held back rather than read by a guess: a wrong guess reads "
    "accented letters as others, and a name from your list written with "
    "other letters would not be replaced. Saved as UTF-8, it reads the "
    "same way in QualCoder too.")
_CHECK_ACCENTS = ("checking first that its accents look right (if they "
                  "do not, the app read it wrongly: choose another "
                  "encoding when you open it)")

HELD_BACK = {
    "names_in_file_name": "This file's own name holds a name from your "
                          "names list, so it is not shown here. You could "
                          "rename the file on your computer, then ask "
                          "again; or, if the name may stay, say so for "
                          "this import (import_file_names_with_listed_"
                          "names), and it comes in under that name, which "
                          "then reaches the AI provider whenever an answer "
                          "names the file.",
    "pdf_listed_names": "This PDF names {names} of the people in your "
                        "list, {count} times. Names in a PDF are never "
                        "replaced, here or in QualCoder; if the assistant "
                        "reads this file, it reads those names. It comes "
                        "in only if you say so for this import "
                        "(import_pdfs_with_listed_names).",
    "not_utf8": "It is not saved as UTF-8, the one form of text Exegete "
                "reads, " + _WHY_NOT_UTF8 + " You could save a copy as "
                "UTF-8 and import that, " + _CHECK_ACCENTS + ": in Word, "
                "open it (if Word asks which encoding to use, pick the "
                "one whose preview reads right), then choose File, Save "
                "As, Plain Text, and "
                "\"Unicode (UTF-8)\" in the window that follows; in "
                "TextEdit on a Mac, open it, then choose File, Duplicate "
                "and File, Save, with \"Unicode (UTF-8)\" as the plain "
                "text encoding; in Notepad on Windows, open it, then "
                "choose File, Save As, with UTF-8 as the encoding.",
    "not_utf8_web": "This web page is not saved as UTF-8, the one form of "
                    "text Exegete reads (whatever character set the page "
                    "declares, since a declaration can be wrong), "
                    + _WHY_NOT_UTF8 + " You could save a copy as UTF-8 "
                    "and import that, " + _CHECK_ACCENTS + ": in Word, "
                    "open the page, then choose File, Save As, Word "
                    "Document (.docx), and import the .docx; in Notepad "
                    "on Windows, open it, then choose File, Save As, with "
                    "UTF-8 as the encoding; in TextEdit on a Mac, first "
                    "tick \"Display HTML files as HTML code\" in its "
                    "settings (Open and Save), open the page, then choose "
                    "File, Duplicate and File, Save, with \"Unicode "
                    "(UTF-8)\" as the plain text encoding.",
    "garbled_rtf": "Its accented letters came out wrong (\"Ã©\" for "
                   "\"é\"), as QualCoder's way of reading RTF gives for "
                   "this file, and names in it would escape your names "
                   "list. Open it in Word or LibreOffice and save it as a "
                   "Word document (.docx), then import that; QualCoder "
                   "reads that file the same way.",
    "garbled_fixed": "Its text holds letters that came out wrong (\"Ã©\" "
                     "for \"é\") in the file itself, and names in it would "
                     "escape your names list. Open it in its own app, "
                     "correct them, save it, then ask again.",
    "not_read_in_time": "Not read in time; ask again for these.",
}

# Said once for a file whose text a warning changes: why the import does
# not mend what QualCoder's way of reading does, and why the ways round
# are chosen as they are.
WHY_AS_QUALCODER = (SAME_READING + " Each way round gives a file QualCoder "
                    "reads the same way too.")
# Said instead when Exegete's reading of the file departs from
# QualCoder's (the departures' lines say how).
WHY_DEPARTED = ("Where Exegete reads this file better than QualCoder's "
                "own import would, the lines for information say how.")
READS_OTHERWISE = "qualcoder_reads_otherwise"
WHY_SUBTITLES = ("QualCoder imports a subtitle file only as a recording's "
                 "transcript, so it has no reading of this document to "
                 "agree with.")


def why_line(subtitles: bool, codes: Sequence[str] = ()) -> str:
    """The line said once for a file whose text a warning changes."""
    if subtitles:
        return WHY_SUBTITLES
    if READS_OTHERWISE in codes:
        return WHY_DEPARTED
    return WHY_AS_QUALCODER


# Sign code -> (group, words). Group "changes" changes what the
# researcher will read; "information" does not.
WARNINGS = {
    # Where Exegete reads the file better than QualCoder's own import
    # (the named departures; TOOLS.md lists them): information, since
    # the text is the better for them.
    "word_line_breaks": ("information",
        "Lines that end without a new paragraph (Shift and Return in "
        "Word) keep their line break. QualCoder's own import would join "
        "the words either side, as in \"thank youInterviewer\"."),
    "word_tab_stops": ("information",
        "Tab stops set on a paragraph add nothing to its text. "
        "QualCoder's own import would put a tab character at the "
        "paragraph's start for each one."),
    "word_text_boxes": ("information",
        "Text in a text box comes in once, after the paragraph it belongs "
        "to. QualCoder's own import would repeat it, up to four times."),
    "word_tracked_changes": ("information",
        "Text moved with tracked changes comes in once, at its new place, "
        "and deleted tabs are left out. QualCoder's own import would keep "
        "moved text at both places."),
    "word_hyphens_tabs": ("information",
        "Non-breaking hyphens and positioned tabs are kept. QualCoder's "
        "own import would leave them out and join the words, as in "
        "\"wellknown\" for \"well-known\"."),
    "word_notes": ("information",
        "Its footnotes, endnotes, comments, headers and footers ({count} "
        "in all) come after the document's text, each labelled, as in "
        "\"Footnote 1: ...\"; comments' authors and dates are left out. "
        "QualCoder's own import would leave them all out."),
    "word_revisions": ("information",
        "It has tracked changes, read as if accepted (insertions in, "
        "deletions out), as QualCoder reads them. To read it another way, "
        "accept or reject the changes in Word first."),
    "odt_spaces": ("information",
        "Runs of spaces are kept. QualCoder's own import would keep only "
        "the first space of each run."),
    "odt_tabs": ("information",
        "Tabs are kept. QualCoder's own import would leave them out, as "
        "in \"Q:Why\" for \"Q:<tab>Why\"."),
    "odt_line_breaks": ("information",
        "Lines that end without a new paragraph keep their line break. "
        "QualCoder's own import would join the words either side."),
    "odt_text_boxes": ("information",
        "Text in a text box starts on a line of its own. QualCoder's own "
        "import would join it to the words before it."),
    "odt_notes": ("information",
        "Its footnotes, endnotes, comments, headers and footers ({count} "
        "in all) come after the document's text, each labelled, as in "
        "\"Footnote 1: ...\"; comments' authors and dates are left out. "
        "QualCoder's own import would leave notes and comments inside the "
        "sentence with their markup (a comment's author and date among "
        "it), and headers and footers out."),
    "odt_markup": ("information",
        "Markup QualCoder's own import would leave in the text is taken "
        "out: other programs' tags, and character codes such as "
        "\"&#233;\", which are read as the letters they stand for."),
    "odt_any_program": ("information",
        "It was not saved by LibreOffice (pandoc and the Mac's TextEdit "
        "write OpenDocument differently). QualCoder's own import would "
        "find no text in it and store the file's own codes instead."),
    "odt_tables": ("information",
        "Tables come in between \"=== TABLE ===\" and \"=== END TABLE "
        "===\" lines, each cell a paragraph of its own, as QualCoder marks "
        "them."),
    "rtf_deleted": ("information",
        "Text deleted with tracked changes is left out. QualCoder's own "
        "import would keep it."),
    "rtf_notes": ("information",
        "Its footnotes, endnotes, comments, headers, footers and text "
        "boxes ({count} in all) come after the document's text, each "
        "labelled, as in \"Footnote 1: ...\"; comments' authors and "
        "dates are left out. QualCoder's own import would leave them all "
        "out."),
    "rtf_emoji": ("information",
        "It holds emoji ({count}), which RTF writes in two halves; each "
        "comes in as one character. QualCoder's own import would fail on "
        "this file."),
    "web_blocks": ("information",
        "Blocks and table cells start on lines of their own. QualCoder's "
        "own import would run them together, as in \"Name:Ana\" for a "
        "table of two cells."),
    READS_OTHERWISE: ("information",
        "So QualCoder's own import of this file would store other text: "
        "if the same file is also imported in QualCoder, codings made on "
        "one copy will not line up on the other. In this project both "
        "programs read the text Exegete stores, and agree on every "
        "coding."),
    "pdf_scanned": ("changes",
        "This PDF is pictures of pages, with no words Exegete can read; "
        "only QualCoder's area coding works on it. QualCoder imports it "
        "the same way. Way round: run text recognition (OCR) on it in "
        "another program, then import the result."),
    "pandoc_wrapped": ("changes",
        "Its lines are broken at 72 characters, as a converter such as "
        "pandoc leaves them; each break stays in the text. See "
        "explain_ai_coding_tools('converted_documents') for converting "
        "without it."),
    "pandoc_tables": ("changes",
        "It has tables drawn with dashes and plus signs, as a converter "
        "such as pandoc draws them. See "
        "explain_ai_coding_tools('converted_documents')."),
    "pandoc_notes": ("changes",
        "It has numbered note markers such as [1], with the notes "
        "gathered at the end, as a converter such as pandoc leaves them. "
        "See explain_ai_coding_tools('converted_documents')."),
    "subtitles": ("changes",
        "A subtitle file comes in line by line, with its timings and "
        "numbers; if your transcription tool can export a Word or text "
        "file, that reads more easily. Brought in as a document, it "
        "cannot later be attached to its recording as QualCoder's "
        "transcript, so its codings would stay on the document."),
    "near_limit": ("changes",
        "Its text is {characters} characters long, more than half "
        "Exegete's limit of {limit}."),
    "astral": ("information",
        "It holds emoji or other rare characters ({count}); after the "
        "first of them, QualCoder shows codings shifted."),
    "invisible": ("information",
        "It holds invisible control characters ({count}), kept as "
        "QualCoder keeps them."),
    "spaces_only": ("information",
        "Its text is only spaces and blank lines, as QualCoder would "
        "store it."),
    "pdf_notes": ("information",
        "Its {count} notes join the file's memo, as QualCoder adds them; "
        "names in them are not replaced."),
    "pdf_markups": ("information",
        "It has {count} highlight or underline marks. QualCoder would "
        "have offered to code them; Exegete codes nothing without your "
        "approval, one by one."),
    "qc382_pdf": ("information",
        "QualCoder 3.8.2's PDF view shows this PDF but will not let you "
        "code it there (its Code text window can); QualCoder 4.0's PDF "
        "view can."),
    "listed_name_in_file_name": ("information",
        "Its own name holds a name from your names list, and it comes in "
        "under that name, as you said: the name reaches the AI provider "
        "whenever an answer names the file, and the project's copy of "
        "the original keeps it."),
}


def say(table: Dict[str, Any], code: str, **numbers: Any) -> str:
    """The fixed words for `code`, with its numbers; a code with no words
    gives the general one, never the code's own text."""
    entry = table.get(code)
    if entry is None:
        entry = FILE_REFUSALS["reader_failed"]
    if isinstance(entry, tuple):
        entry = entry[1]
    try:
        return entry.format(**numbers)
    except (KeyError, IndexError, ValueError):
        return entry.split("{")[0].rstrip(" (") + "."
