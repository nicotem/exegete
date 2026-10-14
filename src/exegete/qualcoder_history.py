# SPDX-License-Identifier: LGPL-3.0-or-later
"""A project's history with QualCoder (v0.15.0; the owner's ruling 73,
item 12: worked out once when the project is selected and consulted by
every text; QualCoder's closing write is not read as "open").

Two questions, kept apart. "Has this project been in QualCoder, and is
QualCoder on this computer?" decides whether notes about QualCoder are
relevant; it is answered here, once per selection, from traces that
last. "Is QualCoder open on it now?" decides whether a write is safe; it
stays the live check at every write and every get_current_project (the
lock file, `database.qualcoder_gui_signals`), and nothing here changes
it.

What is looked at, and nothing else:
1. `<project>/ai_data`, by `is_dir()`: QualCoder 3.8.2 and 4.0 make it
   when they first open a project (3.8.2 ai_chat.py:181-214 from
   __main__.py:3034; 4.0 ai_chat.py:1693-1697 from __main__.py:2894-2895,
   at the tag 4.0); Exegete never makes one. Then, each by `is_file()`
   of its own path, the AI chat history (`ai_data/chat_history.sqlite`,
   made there) and QualCoder 4.0's AI search index
   (`ai_data/search.sqlite`, 4.0 ai_vectorstore.py:582).
2. QualCoder's own backups beside the project: the names in the
   project's parent folder that match `<stem>_BKUP_*.qda`, the stem
   escaped for glob as `earlier_name` reads them, stopping at the first
   that is a folder.
3. A leftover lock file: `database.qualcoder_lock_state` says "stale"
   (it reads the first LOCK_READ_MAX_BYTES of the project's lock file,
   two short lines, with one retry after half a second, as every
   write's check does).
4. Whether QualCoder is installed: its settings folder, `~/.qualcoder`
   (3.8.2 __main__.py:102-105, 4.0 __main__.py:125-131: the home folder
   as Python finds it, on every platform), by `is_dir()` only. Its
   contents (settings and API keys) are never listed, opened or
   measured.
5. Whether QualCoder is running, from the process scan
   (`database._qualcoder_process_scan`), only when asked.

No sign holds a path or a project's name, and nothing is logged with
either: a check that fails is left out and the kind of its error logged
at debug level. Nothing is written. Each check is a public function, so
later texts reuse it rather than repeat it.

The researcher's answer to "Do you also use QualCoder on this computer?"
(EXEGETE_USES_QUALCODER, ruling 73, item 8: yes, no or not sure, the
default) weighs in `History.level` after the signs. A sign on the
project, or a QualCoder running at the selection, decides whatever the
answer; "no" outweighs only QualCoder's settings folder, which says that
QualCoder is installed, not that it is used; "yes" gives the level
"computer" when nothing is found. It never reaches the live check: the
refusal while QualCoder 3.8's lock file is active and the warnings on
signs of a QualCoder 4.0 window never consult this module.
"""

import glob
import logging
from pathlib import Path
from typing import Any, Callable, Dict, NamedTuple, Optional, Tuple, Union

from . import database, names
from .database import error_label

logger = logging.getLogger(__name__)

# The answers to "Do you also use QualCoder on this computer?"
YES = "yes"
NO = "no"
NOT_SURE = "not sure"
ANSWERS = (YES, NO, NOT_SURE)

# Logged once at start (server.main) for a value that is none of the
# three; the value itself is never logged or returned.
SETTING_NOT_RECOGNISED = (
    f"{names.NEW_ONLY_SETTINGS['uses_qualcoder']} is not yes, no or not "
    f"sure; it is read as not sure.")

AI_DATA_SIGN = (
    "an ai_data folder, which QualCoder 3.8.2 and 4.0 make when they "
    "first open a project (Exegete never makes one)")
CHAT_HISTORY_SIGN = (
    "QualCoder's AI chat history (ai_data/chat_history.sqlite)")
SEARCH_INDEX_SIGN = (
    "QualCoder 4.0's AI search index (ai_data/search.sqlite)")
BACKUP_SIGN = (
    "QualCoder's own backups beside the project (_BKUP_ in their names)")
STALE_LOCK_SIGN = (
    "a lock file left in the project by a program that did not close it "
    "cleanly (QualCoder 3.8 leaves one; so can an interrupted write by "
    "Exegete)")

REPORT_NOTE = (
    "What Exegete found when the project was selected; it decides which "
    "notes about QualCoder its answers carry. Whether QualCoder has the "
    "project open now is a separate, live check: select_project's "
    "warning, and get_current_project's qualcoder_open and "
    "qualcoder_gui_signals. A false qualcoder_on_this_computer means "
    "only that no sign of QualCoder was found on this computer.")

PathLike = Union[str, Path]


class History(NamedTuple):
    """What the traces say about a project and this computer.

    `signs`: plain sentences, the traces on this project, in a fixed
    order. `installed`: QualCoder's settings folder is there. `running`:
    True when the process scan found a QualCoder; False when it ran,
    could read command lines and found none, and no line that may be one
    (`ProcessScan.found_none`); None when it was not asked for, could not
    run, saw program names only, or found a line that may be a QualCoder
    it could not read. `setting`: the researcher's answer to "Do you
    also use QualCoder on this computer?", "yes", "no" or "not sure"
    (read_setting).
    """
    signs: Tuple[str, ...]
    installed: bool
    running: Optional[bool]
    setting: str = NOT_SURE

    @property
    def level(self) -> str:
        """"project" when the project shows a trace, whatever the
        setting; otherwise "computer" when QualCoder is running here,
        whatever the setting; otherwise, by the setting: "computer" for
        "yes", "none" for "no", and for "not sure" "computer" when
        QualCoder's settings folder is there, "none" when it is not.
        "No" outweighs the settings folder alone, which says that
        QualCoder is installed, not that it is used."""
        if self.signs:
            return "project"
        if self.running is True:
            return "computer"
        if self.setting == YES:
            return "computer"
        if self.setting == NO:
            return "none"
        if self.installed is True:
            return "computer"
        return "none"


def read_setting(raw: Optional[str]) -> Tuple[str, bool]:
    """The answer to "Do you also use QualCoder on this computer?" from
    the raw value of EXEGETE_USES_QUALCODER (env_settings.uses_qualcoder),
    and whether it was recognised. The value is stripped, put in lower
    case and its inner runs of white space made one space: "yes", "no"
    or "not sure". Unset, empty, or a placeholder the app left unfilled
    (`${...}`) is "not sure", recognised; any other word is "not sure",
    not recognised (server.main logs SETTING_NOT_RECOGNISED once)."""
    if raw is None:
        return NOT_SURE, True
    word = " ".join(raw.split()).lower()
    if not word or word.startswith("${"):
        return NOT_SURE, True
    if word in ANSWERS:
        return word, True
    return NOT_SURE, False


def _checked(check: Callable[[], Any]) -> bool:
    """A check's answer, or False when it could not be made. Only the
    kind of error is logged (`error_label`), at debug level: its message
    can hold a path."""
    try:
        return bool(check())
    except Exception as error:
        logger.debug("A trace of QualCoder could not be checked: %s",
                     error_label(error))
        return False


def ai_data_found(project_folder: PathLike) -> bool:
    """The project folder holds an `ai_data` folder."""
    return _checked(lambda: (Path(project_folder) / "ai_data").is_dir())


def _ai_data_file_found(project_folder: PathLike, name: str) -> bool:
    return _checked(
        lambda: (Path(project_folder) / "ai_data" / name).is_file())


def qualcoder_backup_beside(project_folder: PathLike) -> bool:
    """A folder named `<stem>_BKUP_*.qda` sits beside the project: one of
    QualCoder's own backups. Its absence proves nothing (QualCoder
    deletes a session's backup when nothing changed)."""
    def look() -> bool:
        folder = Path(project_folder)
        pattern = glob.escape(folder.stem) + "_BKUP_*.qda"
        for entry in folder.parent.glob(pattern):
            if entry.is_dir():
                return True
        return False
    return _checked(look)


def stale_lock_found(project_folder: PathLike) -> bool:
    """The project's lock file is there and not refreshed: left by a
    program that did not close it cleanly."""
    return _checked(
        lambda: database.qualcoder_lock_state(project_folder)[0] == "stale")


def settings_folder_present(home: Optional[PathLike] = None) -> bool:
    """QualCoder's settings folder, `~/.qualcoder`, is a folder. Only
    that is asked: nothing inside it is listed, opened or measured."""
    return _checked(
        lambda: ((Path(home) if home is not None else Path.home())
                 / ".qualcoder").is_dir())


def _running(scan_processes: bool) -> Optional[bool]:
    if not scan_processes:
        return None
    try:
        # Looked up at call time, so that a test's replacement reaches it
        scan = database._qualcoder_process_scan()
    except Exception as error:
        logger.debug("The process scan failed: %s", error_label(error))
        return None
    if scan is None:
        return None
    if scan.hits:
        return True
    return False if scan.found_none else None


def work_out(project_folder: PathLike, *, scan_processes: bool,
             home: Optional[PathLike] = None,
             setting: str = NOT_SURE) -> History:
    """The project's history with QualCoder, from the five checks above,
    in their order, with `setting`, the answer read_setting gives. It
    never raises. With `scan_processes` False no scan is called and
    `running` is None."""
    signs = []
    if ai_data_found(project_folder):
        signs.append(AI_DATA_SIGN)
    if _ai_data_file_found(project_folder, "chat_history.sqlite"):
        signs.append(CHAT_HISTORY_SIGN)
    if _ai_data_file_found(project_folder, "search.sqlite"):
        signs.append(SEARCH_INDEX_SIGN)
    if qualcoder_backup_beside(project_folder):
        signs.append(BACKUP_SIGN)
    if stale_lock_found(project_folder):
        signs.append(STALE_LOCK_SIGN)
    return History(tuple(signs), settings_folder_present(home),
                   _running(scan_processes), setting)


def report(history: Optional[History]) -> Optional[Dict[str, Any]]:
    """The answer field `qualcoder_history`, or None (the field left
    out) when there is no history, or when the level is "none" and the
    setting "not sure". `setting` is the researcher's answer, so that the
    assistant knows it and does not ask again."""
    if history is None:
        return None
    if history.level == "none" and history.setting == NOT_SURE:
        return None
    return {
        "signs_on_this_project": list(history.signs),
        "qualcoder_on_this_computer": (history.installed is True
                                       or history.running is True),
        "note": REPORT_NOTE,
        "setting": history.setting,
    }
