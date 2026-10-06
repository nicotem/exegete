# SPDX-License-Identifier: LGPL-3.0-or-later
"""What the document import says, in plain words (0.14.3, provisional).

Every refusal and warning the import gives is one of these fixed texts
with numbers, never a library's message or a document's own words: a
hostile document can put instructions in an archive entry's name or a
PDF object's, and an error message would carry them. Each warning says
what the researcher will see, what to do, and why.
"""

from typing import Any, Dict, List, Optional

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
    "odt_not_libreoffice": "QualCoder cannot find the text in this "
                           "OpenDocument file, because it was not saved by "
                           "LibreOffice (pandoc and the Mac's TextEdit write "
                           "it differently); QualCoder would store the "
                           "file's own codes as its text. Open it in "
                           "LibreOffice and save it again as .odt, or save "
                           "it as Word (.docx), then import that.",
    "empty": "This file is empty.",
    "pdf_password": "This PDF is protected by a password. Save a copy "
                    "without the password (in Preview or Acrobat), then "
                    "import that.",
    "named_encoding_does_not_fit": "This file does not read as the "
                                   "character set named ({encoding}).",
    "unstorable": "This file holds a character a project cannot store "
                  "(QualCoder's import fails on it too). Open it in its "
                  "own app and save a fresh copy.",
    "unstorable_rtf": "It holds an emoji, or another character RTF writes "
                      "in two halves, which neither QualCoder nor Exegete "
                      "can store (QualCoder's import fails on it). Save it "
                      "as Word (.docx) in its app, or remove the emoji, "
                      "then import that.",
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

HELD_BACK = {
    "names_in_file_name": "This file's own name holds a name from your "
                          "names list, so it is not shown here. Rename "
                          "the file on your computer, then ask again.",
    "pdf_listed_names": "This PDF names {names} of the people in your "
                        "list, {count} times. Names in a PDF are never "
                        "replaced, here or in QualCoder; if the assistant "
                        "reads this file, it reads those names. It comes "
                        "in only if you say so for this import "
                        "(import_pdfs_with_listed_names).",
    "garbled": "Its accented letters came out wrong (\"Ã©\" for \"é\", or "
               "letters from another alphabet), so the character set is "
               "probably not the one guessed, and names in it would escape "
               "your names list. Name the character set (for example "
               "cp1252, Windows Western, or mac_roman) with the encoding "
               "argument and ask again, or open the file in its own app "
               "and save it as UTF-8.",
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
    "charset_names": "Its character set was guessed as {charset}, and "
                     "read that way, names from your list come out with "
                     "other letters (as in \"Agnčs\" for \"Agnès\"), "
                     "so the list would not replace them; read as "
                     "{found}, it finds them. Name that character set "
                     "with the encoding argument (encoding=\"{encoding}\") "
                     "and ask again, or open the file in its own app and "
                     "save it as UTF-8.",
    "not_read_in_time": "Not read in time; ask again for these.",
}

TO_WORD_TEXT = ("Way round: in Word, choose File, Save As, Plain Text, "
                "\"Unicode (UTF-8)\", and import the .txt.")
LIBREOFFICE_TO_WORD = ("Way round: in LibreOffice, choose File, Save As, "
                       "Word, and import the .docx (QualCoder's Word "
                       "reading leaves comments and notes out and keeps "
                       "tabs).")
ACCEPT_CHANGES = ("Way round: accept or reject all changes, save, then "
                  "import.")
COPY_INTO_TEXT = ("To code them, copy them into the document's own text "
                  "first, then import it.")
# Said once for a file whose text a warning changes: why the import does
# not mend what QualCoder's way of reading does, and why the ways round
# are chosen as they are.
WHY_AS_QUALCODER = (SAME_READING + " Each way round gives a file QualCoder "
                    "reads the same way too.")
WHY_GUESSED = (SAME_READING + " Saving the file as UTF-8 gives a file "
               "QualCoder reads the same way too; naming the character set "
               "does not, since QualCoder keeps its own guess.")
WHY_SUBTITLES = ("QualCoder imports a subtitle file only as a recording's "
                 "transcript, so it has no reading of this document to "
                 "agree with.")
# A web page whose text is not UTF-8: QualCoder's import fails on it, so
# Exegete reads it by its declared character set, or a named or guessed
# one.
WHY_WEB = ("QualCoder cannot import this web page (its text is not "
           "UTF-8), so there is no QualCoder reading to agree with. "
           "Saving the page as UTF-8 gives a file both programs read the "
           "same way.")
WHY_WEB_GUESSED = (WHY_WEB + " If its accents look wrong, name the "
                   "character set and ask again (encoding=\"cp1252\" for a "
                   "page saved on Windows).")


def why_line(subtitles: bool, codes: List[str],
             web: Optional[str] = None) -> str:
    """The line said once for a file whose text a warning changes. `web`
    is "guessed" or "read" for a web page QualCoder cannot import (its
    text is not UTF-8), read by a guessed character set or by its
    declared or named one."""
    if subtitles:
        return WHY_SUBTITLES
    if web == "guessed":
        return WHY_WEB_GUESSED
    if web:
        return WHY_WEB
    if "charset_guessed_check" in codes:
        return WHY_GUESSED
    return WHY_AS_QUALCODER


# A guessed character set of one byte a letter that is not Western:
# what can go wrong, and the way round for each family of languages.
_DOUBTFUL_GUESS = (
    "Such a guess is often wrong (an ordinary Western European file "
    "saved on Windows is often read as Central European), and then every "
    "accented letter reads as another (\"è\" as \"č\", \"ã\" as "
    "\"ă\"). Way round: name the character set the file was saved in and "
    "ask again (encoding=\"cp1252\" for Western European text saved on "
    "Windows, \"mac_roman\" for a file from an old Mac, and \"cp1250\", "
    "\"cp1257\" or \"cp1254\" for Central European, Baltic or Turkish "
    "text saved on Windows), or save the file as UTF-8 in its own app.")

# Sign code -> (group, words). Group "changes" changes what the
# researcher will read; "information" does not.
WARNINGS = {
    "word_line_break": ("changes",
        "Lines that end without a new paragraph (Shift and Return in "
        "Word) come in joined to the next line's words, as in \"thank "
        "youInterviewer\". " + TO_WORD_TEXT),
    "word_tab_stops": ("changes",
        "Tab stops set on a paragraph come in as tab characters at its "
        "start. " + TO_WORD_TEXT),
    "word_text_box": ("changes",
        "Text in text boxes comes in more than once (up to four times). "
        + TO_WORD_TEXT),
    "word_tracked_changes": ("changes",
        "It has tracked changes: insertions come in as if accepted, and "
        "deletions are left out. " + ACCEPT_CHANGES),
    "word_moved_text": ("changes",
        "It has text moved with tracked changes, which comes in twice. "
        + ACCEPT_CHANGES),
    "word_table": ("changes",
        "Each table cell comes in as a paragraph of its own. "
        + TO_WORD_TEXT),
    "word_headers_footers": ("changes",
        "Headers and footers are left out. " + COPY_INTO_TEXT),
    "word_footnotes": ("changes",
        "Footnotes and endnotes are left out. " + COPY_INTO_TEXT),
    "word_comments": ("changes",
        "Comments are left out. " + COPY_INTO_TEXT),
    "odt_comments": ("changes",
        "Comments leave markup in the text, their author and date among "
        "it, as in \"<dc:creator>Ana</dc:creator>\". "
        + LIBREOFFICE_TO_WORD),
    "odt_notes": ("changes",
        "Footnotes leave markup in the text, as in "
        "\"<text:note-citation>1</text:note-citation>\". "
        + LIBREOFFICE_TO_WORD),
    "odt_tabs": ("changes",
        "Tabs are lost, as in \"Q:Why\" for \"Q:<tab>Why\". "
        + LIBREOFFICE_TO_WORD),
    "odt_spaces": ("changes",
        "Runs of spaces are lost. " + LIBREOFFICE_TO_WORD),
    "odt_line_breaks": ("changes",
        "Lines that end without a new paragraph come in joined to the "
        "next line's words. " + LIBREOFFICE_TO_WORD),
    "odt_tables": ("changes",
        "Tables come in between \"=== TABLE ===\" lines, each cell on a "
        "line of its own. " + LIBREOFFICE_TO_WORD),
    "web_blocks": ("changes",
        "Blocks and table cells run together, as in \"Name:Ana\" for a "
        "table of two cells. Way round: open the page in a word "
        "processor, save it as a Word document (.docx), and import "
        "that."),
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
    "charset_guessed": ("information",
        "Its character set was guessed as {charset}; QualCoder may guess "
        "differently."),
    "charset_guessed_check": ("changes",
        "Its character set was guessed as {charset}; QualCoder may guess "
        "differently. " + _DOUBTFUL_GUESS),
    # The same for a web page whose text is not UTF-8, which QualCoder
    # does not guess for: its import fails on such a page.
    "web_charset_guessed": ("information",
        "Its character set was guessed as {charset}. QualCoder cannot "
        "import this web page, since its text is not UTF-8."),
    "web_charset_guessed_check": ("changes",
        "Its character set was guessed as {charset}. " + _DOUBTFUL_GUESS),
    "charset_named": ("information",
        "It was read as {charset}, the character set named; the memo "
        "records it."),
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
