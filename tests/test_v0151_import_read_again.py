# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.1: import_documents reads each file again before its backup.

Under the project's lock file and before the backup's tree is copied,
each ready file is read again in the order the import takes them and
under its rule for time, and its digest compared with the preview's: a
file changed, gone or grown past its limit is refused with no backup
(the races are in test_v0151_one_backup.py). These pin where the read
happens and that it keeps the import's rule for time: a file there is no
time left for is left for the next call, unread, as the import leaves it.

The reading is faked on test_v0143_import_call_time's clock, which moves
only when a file's text is read.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import exegete.server as server  # noqa: E402
from exegete import doc_import  # noqa: E402
from exegete.database import QUALCODER_LOCK_FILENAME  # noqa: E402

from test_v0143_import_call_time import (  # noqa: E402,F401
    _call, _files, _rows, _scratch_is_not_hidden, clock, folder, project)


def _backups(project):
    return sorted(p.name for p in project.parent.iterdir()
                  if p.name.startswith(f"{project.stem}_backup_"))


def _at_the_sweep(monkeypatch, then):
    """The import's sweep of its old copies, then `then()`: the first
    thing it does under the lock file, before the read again."""
    real = doc_import.sweep_temporary_copies
    fired = []

    def sweep(documents):
        swept = real(documents)
        if not fired:
            fired.append(True)
            then()
        return swept
    monkeypatch.setattr(doc_import, "sweep_temporary_copies", sweep)
    return fired


def test_the_read_again_is_under_the_lock_file_and_before_the_backup(
        project, folder, clock, monkeypatch):
    _files(folder, (5, 5), (5, 5))
    preview, _took = _call(clock, paths=[str(folder)])
    real = doc_import.read_again
    seen = []

    def read_again(result, ctx, now=None):
        seen.append(((project / QUALCODER_LOCK_FILENAME).exists(),
                     _backups(project)))
        return real(result, ctx, now)
    monkeypatch.setattr(doc_import, "read_again", read_again)
    done, _took = _call(clock, paths=[str(folder)],
                        preview_token=preview["preview_token"])
    assert done["success"] is True, done
    assert seen == [(True, [])]
    assert len(_backups(project)) == 1


def test_a_file_there_is_no_time_for_is_left_unread(project, folder, clock,
                                                     monkeypatch):
    """The call's time spent when the import takes the lock: the first
    file is read again (it always has its time), the second is left for
    the next call and not read, so a change to it refuses nothing; the
    import takes the first."""
    _files(folder, (5, 5), (5, 5))
    preview, _took = _call(clock, paths=[str(folder)])

    def spend_the_time_and_change_the_second():
        clock.now += doc_import.TERMINAL_CALL_SECONDS + 60
        (folder / "P02.txt").write_text("preview=5 import=5\nChanged.\n",
                                        encoding="utf-8")
    fired = _at_the_sweep(monkeypatch, spend_the_time_and_change_the_second)
    done, _took = _call(clock, paths=[str(folder)],
                        preview_token=preview["preview_token"])
    assert fired, "the time was never spent; the test proves nothing"
    assert done["success"] is True, done
    assert [f["name"] for f in done["files"]] == ["P01.txt"]
    assert done["not_imported_this_time"]["files"] == ["P02.txt"]
    assert _rows(project) == ["P01.txt"]


def test_a_changed_file_is_refused_in_the_imports_words(project, folder,
                                                         clock, monkeypatch):
    _files(folder, (5, 5), (5, 5))
    preview, _took = _call(clock, paths=[str(folder)])
    fired = _at_the_sweep(monkeypatch, lambda: (folder / "P01.txt")
                          .write_text("preview=5 import=5\nChanged.\n",
                                      encoding="utf-8"))
    done = json.loads(server.import_documents(
        paths=[str(folder)], preview_token=preview["preview_token"]))
    assert fired, "the file never changed; the test proves nothing"
    assert done == {"error": doc_import.BATCH_FAILURES["changed"],
                    "nothing_changed": True}
    assert _backups(project) == []
    assert _rows(project) == []
