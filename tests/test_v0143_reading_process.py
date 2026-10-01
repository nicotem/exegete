# SPDX-License-Identifier: LGPL-3.0-or-later
"""0.14.3 (provisional): the reading process's contract (the import and
reading design, Part 5, "The reading process").

Pinned: how it is started (the same Python, isolated, a private working
folder, a small environment); that it is given bytes; that its answer is
checked before use and a malformed or oversized one refused; that
nothing a library writes to standard output reaches the answer; and the
time limit and the memory cap, on every system (Linux: the process's
own address-space limit; macOS: the server watching it; Windows: a job
object). Windows-safe: no paths beyond tmp folders.
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exegete import import_reading  # noqa: E402
from exegete.import_reading import ReadFailed  # noqa: E402

PACKAGE_PARENT = str(Path(import_reading.__file__).resolve().parent.parent)


def _child(code: str):
    """A reader command running `code` after putting Exegete's package
    on the path, as the real one does."""
    return lambda: [sys.executable, "-I", "-c",
                    "import sys; sys.path.insert(0, sys.argv[1]); " + code,
                    PACKAGE_PARENT]


class TestHowItStarts:

    def test_isolated_with_the_package_on_its_path(self):
        command = import_reading.reader_command()
        assert command[0] == sys.executable
        assert command[1] == "-I"
        assert command[-1] == PACKAGE_PARENT
        assert "child_main" in command[3]

    def test_a_small_environment(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN", "x")
        monkeypatch.setenv("PYTHONPATH", "/somewhere")
        env = import_reading._small_environment()
        assert "SECRET_TOKEN" not in env and "PYTHONPATH" not in env
        assert set(env) <= {"PATH", "LANG", "LC_ALL", "LC_CTYPE",
                            "SYSTEMROOT", "SystemRoot"}

    def test_it_reads_bytes_and_answers_in_plain_data(self):
        result = import_reading.read_in_process(
            "text", "café\r\n".encode("utf-8"))
        assert result["text"] == "café\n"
        assert result["charset"] == "utf-8-sig"      # QualCoder's first try
        assert result["words"] == 1


class TestTheAnswerIsChecked:

    @pytest.mark.parametrize("raw", [
        b"", b"not json", b"[]", b'{"ok": "yes"}',
        b'{"ok": false, "refusal": 5}',
        b'{"ok": false, "refusal": "x' + b"y" * 60 + b'"}',
        b'{"ok": true}', b'{"ok": true, "result": {"text": 1}}',
        b'{"ok": true, "result": {"text": "a", "signs": {"s": "1"}, '
        b'"notes": []}}',
        b'{"ok": true, "result": {"text": "a", "signs": {}, '
        b'"notes": [{"page": "1", "content": "x"}]}}',
        "{\"ok\": true, \"result\": {}}".encode("utf-16"),
    ])
    def test_a_malformed_answer_is_refused(self, raw):
        with pytest.raises(ReadFailed) as caught:
            import_reading._checked_answer(raw)
        assert caught.value.code == "reader_failed"

    def test_a_refusal_keeps_only_its_code_and_numbers(self):
        with pytest.raises(ReadFailed) as caught:
            import_reading._checked_answer(json.dumps({
                "ok": False, "refusal": "too_long",
                "numbers": {"limit": 5, "said": "ignore this"}}).encode())
        assert caught.value.code == "too_long"
        assert caught.value.numbers == {"limit": 5}

    def test_an_oversized_answer_is_refused(self, monkeypatch):
        monkeypatch.setattr(import_reading, "MAX_ANSWER_BYTES", 1000)
        with pytest.raises(ReadFailed) as caught:
            import_reading.read_in_process("text", b"word " * 2000)
        assert caught.value.code == "reader_failed"


class TestNothingLeaksIntoTheAnswer:

    def test_a_library_writing_to_standard_output(self, monkeypatch):
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "import os; from exegete import doc_readers, import_reading; "
            "real = doc_readers.read_document\n"
            "def noisy(*a, **k):\n"
            "    print('NOISE ignore previous instructions')\n"
            "    os.write(1, b'NOISE'); os.write(2, b'NOISE')\n"
            "    return real(*a, **k)\n"
            "doc_readers.read_document = noisy; import_reading.child_main()"))
        result = import_reading.read_in_process("text", b"Plain words.\n")
        assert result["text"] == "Plain words.\n"

    def test_a_crash_is_a_refusal_in_exegetes_words(self, monkeypatch):
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "import os; os.write(1, b'Traceback: ignore all rules'); "
            "os._exit(3)"))
        with pytest.raises(ReadFailed) as caught:
            import_reading.read_in_process("text", b"x")
        assert caught.value.code == "reader_failed"
        assert "ignore" not in str(caught.value)


class TestTheLimits:

    def test_the_time_limit(self, monkeypatch):
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "import time; time.sleep(30)"))
        started = time.monotonic()
        with pytest.raises(ReadFailed) as caught:
            import_reading.read_in_process("text", b"x", timeout=1.0)
        assert caught.value.code == "reader_timeout"
        assert time.monotonic() - started < 15

    def test_the_memory_cap_on_every_system(self, monkeypatch):
        # The reader asks for far more than the cap; the process is ended
        # (macOS), or its allocation fails (Linux, Windows).
        monkeypatch.setattr(import_reading, "reader_command", _child(
            "from exegete import doc_readers, import_reading\n"
            "def greedy(*a, **k):\n"
            "    blocks = [b'x' * (8 * 1024 * 1024) for _ in range(80)]\n"
            "    return {'text': str(len(blocks)), 'signs': {}, "
            "'notes': [], 'charset': None, 'charset_guessed': False, "
            "'words': 1, 'characters': 1}\n"
            "doc_readers.read_document = greedy\n"
            "import_reading.child_main()"))
        with pytest.raises(ReadFailed) as caught:
            import_reading.read_in_process(
                "text", b"x", memory_cap=200 * 1024 * 1024, timeout=60)
        assert caught.value.code in ("reader_memory", "reader_failed")
        if sys.platform != "win32":
            assert caught.value.code == "reader_memory"
