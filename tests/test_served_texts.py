# SPDX-License-Identifier: LGPL-3.0-or-later
"""The tool descriptions Exegete serves are the committed ones.

scripts/served_texts.py renders every description of both tool sets,
`full` and `core`, and tests/fixtures/served_descriptions.txt holds the
render as it was last written and reviewed. A change to any description,
or to a paragraph several descriptions share, fails here until the dump
is written again (`python scripts/served_texts.py write`, on Python
3.13) and its diff read. Python 3.13 strips docstring indentation that
earlier versions keep, so the comparison is exact on 3.13 and sets
white space aside on any other version.
"""
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "served_texts", REPO / "scripts" / "served_texts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_served_descriptions_are_the_committed_ones(script):
    rendered = script.render()
    # Read as text, so that a checkout with Windows line ends reads the
    # same; the render itself holds none
    committed = script.DUMP.read_text(encoding="utf-8")
    assert "\r" not in rendered
    exact = sys.version_info[:2] == script.EXACT_ON
    diff = script.differences(rendered, committed, exact)
    assert not diff, "\n".join(diff + [
        "A served description differs from the dump: write the dump "
        "again with `python scripts/served_texts.py write` on Python "
        "3.13, and review its diff."])


def test_the_environment_is_pinned(script):
    environ = {"HOME": "home", "USERPROFILE": "home", "TMPDIR": "tmp",
               "UV_CACHE_DIR": "cache", "EXEGETE_TOOLSET": "core",
               "QUALCODER_MCP_TOOLSET": "core", "PATH": "bin"}
    folder = script.pin_environment(environ)
    try:
        for key in ("HOME", "USERPROFILE", "TMPDIR", "UV_CACHE_DIR"):
            assert folder in Path(environ[key]).parents, key
            assert Path(environ[key]).is_dir(), key
        assert "EXEGETE_TOOLSET" not in environ
        assert "QUALCODER_MCP_TOOLSET" not in environ
        assert environ["PATH"] == "bin"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_the_dump_is_written_on_python_3_13_alone(script):
    assert script.refusal("write", (3, 13, 5)) is None
    for version in ((3, 10, 18), (3, 11, 13), (3, 12, 0), (3, 14, 0)):
        assert script.refusal("write", version), version
    assert script.refusal("render", (3, 11, 13)) is None
    assert script.refusal("check", (3, 11, 13)) is None
