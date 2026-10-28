# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.15.2: the documents' commands, run in CI (scripts/doc_commands.py).

Pinned here: how the marks make sessions and steps; that a mark the
script cannot run is named by its file and line; the first set of marks,
by session, in whichever document holds it; the substitutions, and only
those. Then, in bash with a terminal (Linux and macOS; CI runs the
sessions on Ubuntu): a session's own home, with nothing of the caller's
settings or PATH; each expectation matched against its own step alone;
and a waiting program stopped with one Ctrl+C, the terminal closed and
then a kill when it does not stop, and which of the three ended it.
"""

import importlib.util
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location(
        "doc_commands", REPO / "scripts" / "doc_commands.py")
    module = importlib.util.module_from_spec(spec)
    # registered first: its dataclasses look the module up by name
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


doc_commands = _script()

needs_bash = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="a session runs in bash with a terminal, on Linux and macOS; CI "
           "runs the documents' sessions on Ubuntu")

GUIDE = """\
# A guide

Install it:

<!-- ci: run one -->
```bash
cd ~
echo first
# Example output: first
echo second
# Example output: second
```

1. In a list:

   <!-- ci: run two, one -->
   ```bash
   echo indented
   ```

```text
<!-- ci: run four -->
```

The command `echo in a sentence` runs too.

<!-- ci: run two: echo in a sentence -->
<!-- ci: expect two: in a sentence -->

```bash
sleep 600
```

<!-- ci: run one waits: sleep 600 -->
<!-- ci: expect one: ready -->

<!-- ci: run three waits -->
```bash
cd /tmp
python3 -m http.server
```
"""


def _at(text, line):
    return text.split("\n").index(line) + 1


def test_marks_make_sessions_and_steps_in_document_order():
    sessions = doc_commands.read_sessions("guide.md", GUIDE)
    read = [(session.file, session.name,
             [(step.line, step.command, step.waits, step.expects)
              for step in session.steps]) for session in sessions]
    at = lambda line: _at(GUIDE, line)  # noqa: E731
    assert read == [
        ("guide.md", "one", [
            (at("cd ~"), "cd ~\necho first", False,
             [(at("# Example output: first"), "first")]),
            (at("echo second"), "echo second", False,
             [(at("# Example output: second"), "second")]),
            (at("   echo indented"), "echo indented", False, []),
            (at("<!-- ci: run one waits: sleep 600 -->"), "sleep 600", True,
             [(at("<!-- ci: expect one: ready -->"), "ready")])]),
        ("guide.md", "two", [
            (at("   echo indented"), "echo indented", False, []),
            (at("<!-- ci: run two: echo in a sentence -->"),
             "echo in a sentence", False,
             [(at("<!-- ci: expect two: in a sentence -->"),
               "in a sentence")])]),
        ("guide.md", "three", [
            (at("cd /tmp"), "cd /tmp", False, []),
            (at("python3 -m http.server"), "python3 -m http.server", True,
             [])]),
    ]


@pytest.mark.parametrize("text, line", [
    # a command not found between the mark and the heading above it
    ("```bash\necho before\n```\n\n## Next\n\nText.\n\n"
     "<!-- ci: run s: echo before -->\n", 9),
    # a mark above a block other than bash, and above no block
    ("Text.\n\n<!-- ci: run s -->\n```json\n{}\n```\n", 3),
    ("<!-- ci: run s -->\n\nText.\n", 1),
    # a word the script does not know, a mark over two lines
    ("Text.\n\n<!-- ci: check s -->\n", 3),
    ("<!-- ci: run s\n-->\n```bash\necho x\n```\n", 1),
    # a run mark after the session's waiting program
    ("```bash\nsleep 9\necho x\n```\n\n<!-- ci: run s waits: sleep 9 -->\n"
     "<!-- ci: run s: echo x -->\n", 7),
    # an expectation with no step before it, a session called `waits`
    ("<!-- ci: expect s: x -->\n", 1),
    ("```bash\nls\n```\n<!-- ci: run waits: ls -->\n", 4),
    # a mark at another indentation than its block's, which would end
    # the list the block is in
    ("1. Item:\n\n<!-- ci: run s -->\n   ```bash\n   echo x\n   ```\n", 3),
    # an example line with no command above it in its block
    ("<!-- ci: run s -->\n```bash\n# Example output: x\necho x\n```\n", 3),
])
def test_a_bad_mark_is_named_by_file_and_line(text, line):
    with pytest.raises(doc_commands.BadMark) as refused:
        doc_commands.read_sessions("guide.md", text)
    assert str(refused.value).startswith(f"guide.md:{line}: ")


# Each session of the first set: the commands its steps hold, in order,
# and what each is expected to print
FIRST_SET = {
    "dev": [("git clone https://github.com/<you>/exegete.git", None),
            ('pip install -e ".[dev,pdf-epub]"', None)],
    "source": [("git clone https://github.com/nicotem/exegete.git", None),
               ("pip install -e .", None),
               ("which python",
                "/Users/yourname/Documents/exegete/venv/bin/python"),
               ("whoami", "yourname")],
    # v0.15.2: the Terminal guide's commands install the optional part
    # for PDF and EPUB, as README's does
    "venv": [("python3 -m venv ~/exegete-venv", None),
             ('~/exegete-venv/bin/pip install "exegete[pdf-epub]"', None),
             ("~/exegete-venv/bin/exegete --version", "exegete <version>")],
    "pipx": [('pipx install "exegete[pdf-epub]"', None),
             ("which exegete", None),
             ("exegete --version", "exegete <version>")],
    "uv": [('uv tool install "exegete[pdf-epub]"', None),
           ("which exegete", None),
           ("exegete --version", "exegete <version>")],
}


def test_the_first_set_is_marked():
    """Found by session, in whichever tracked document holds it, so a
    move to another guide keeps it; a session split across two
    documents, or a mark lost in a move, fails here."""
    sessions, bad = doc_commands.read_all(REPO)
    assert not bad, bad
    for name, wanted in FIRST_SET.items():
        found = [session for session in sessions if session.name == name]
        assert len(found) == 1, (name, [session.file for session in found])
        steps, index = found[0].steps, 0
        for command, printed in wanted:
            # in order; a block's step may hold several of them
            while index < len(steps) and command not in steps[index].command:
                index += 1
            assert index < len(steps), (name, command)
            if printed is not None:
                assert printed in [
                    words for _, words in steps[index].expects], \
                    (name, command)


def test_only_the_listed_substitutions_apply():
    checkout, quoted = "/work/the checkout", "'/work/the checkout'"
    lines = [
        "git clone https://github.com/nicotem/exegete.git",
        "git clone https://github.com/<you>/exegete.git  # your fork",
        "git clone https://github.com/nicotem/exegete.git elsewhere",
        "~/exegete-venv/bin/pip install exegete",
        'pipx install --force "exegete[pdf-epub]"',
        "uv tool install exegete",
        'export EXEGETE_PROJECT_PATH="/path/to/your/project.qda"',
        "pip install exegete-tools",
        "pip install -e .",
        "git clone https://github.com/ccbogel/QualCoder.git",
        "exegete --version",
        "export EXEGETE_CODER_NAME=me",
    ]
    assert doc_commands.substitute("\n".join(lines), checkout).split(
        "\n") == [
        f"git clone {quoted} exegete",
        f"git clone {quoted} exegete  # your fork",
        f"git clone {quoted} elsewhere",
        f"~/exegete-venv/bin/pip install {quoted}",
        "pipx install --force '/work/the checkout[pdf-epub]'",
        f"uv tool install {quoted}",
    ] + lines[7:]


def test_an_expectation_reads_its_placeholders():
    pattern = doc_commands.expectation("exegete <version>", "/h", "me")
    for printed in ("exegete 0.15.1a1\n", "exegete 1.0",
                    "exegete 0.15.2rc1.post2.dev3"):
        assert pattern.search(printed), printed
    for printed in ("exegete (pyproject.toml)", "exegete 0.15.1abc",
                    "exegete 0.15.", "exegete version"):
        assert not pattern.search(printed), printed
    assert doc_commands.expectation(
        "~/x and /Users/yourname/y, yourname", "/h", "me").fullmatch(
        "/h/x and /h/y, me")


def test_the_scratch_folder_is_new_or_empty_and_never_the_home(
        tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    (tmp_path / "used").mkdir()
    (tmp_path / "used" / "a file").write_text("x")
    (tmp_path / "empty").mkdir()
    assert doc_commands.scratch_problem(tmp_path / "home")
    assert doc_commands.scratch_problem(tmp_path / "used")
    assert doc_commands.scratch_problem(tmp_path / "used" / "a file")
    assert doc_commands.scratch_problem(tmp_path / "empty") is None
    assert doc_commands.scratch_problem(tmp_path / "new") is None
    with pytest.raises(ValueError):
        doc_commands.run_sessions([], tmp_path / "used", str(REPO))


def test_no_mark_at_all_fails(monkeypatch, capsys):
    """A change to the marks' form must not leave the job reading
    nothing and passing."""
    monkeypatch.setattr(doc_commands, "read_all", lambda root: ([], []))
    assert doc_commands.main(["--list"]) == 1


def _run(tmp_path, text):
    return doc_commands.run_sessions(
        doc_commands.read_sessions("guide.md", text), tmp_path / "scratch",
        str(REPO))


# What a runner or a developer's computer may set, which a session must
# not see: pipx's home, a virtual environment, the folders programs on
# Linux follow, and uv's folder for tools
OUTSIDE = ("PIPX_HOME", "VIRTUAL_ENV", "XDG_CACHE_HOME", "XDG_DATA_HOME",
           "UV_TOOL_DIR")


@needs_bash
def test_a_session_has_a_scratch_home_and_nothing_of_the_runners(
        tmp_path, monkeypatch):
    home, own = tmp_path / "test-home", tmp_path / "own"
    home.mkdir()
    own.mkdir()
    (own / "exegete").write_text("#!/bin/sh\necho a stand-in\n")
    (own / "exegete").chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", f"{own}{os.pathsep}{os.environ['PATH']}")
    for name in OUTSIDE:
        monkeypatch.setenv(name, str(tmp_path / name))
    [outcome] = _run(tmp_path, (
        "<!-- ci: run s -->\n```bash\n"
        'echo "HOME=$HOME"\necho "USERPROFILE=$USERPROFILE"\n'
        'echo "TMPDIR=$TMPDIR"\necho "UV_CACHE_DIR=$UV_CACHE_DIR"\n'
        'env\ncommand -v exegete || echo "no exegete"\n```\n'))
    assert outcome.failures == []
    lines = outcome.outputs[0].splitlines()
    settings = dict(line.split("=", 1) for line in lines if "=" in line)
    scratch = (tmp_path / "scratch").resolve()
    for name in ("HOME", "USERPROFILE", "TMPDIR", "UV_CACHE_DIR"):
        assert Path(settings[name]).is_relative_to(scratch), name
    assert settings["HOME"] == settings["USERPROFILE"]
    assert settings["EXEGETE_UPDATE_CHECK"] == "off"
    assert not set(OUTSIDE) & set(settings), settings
    assert "no exegete" in lines, lines
    assert list(home.iterdir()) == []


@needs_bash
def test_an_expectation_is_matched_against_its_step_alone(tmp_path):
    text = (
        "```bash\n"
        'echo "installed package exegete 1.2.3"\ntrue\n'
        'echo "exegete 0.15.1a1"\necho "exegete (pyproject.toml)"\n```\n\n'
        '<!-- ci: run s: echo "installed package exegete 1.2.3" -->\n'
        "<!-- ci: run s: true -->\n"
        "<!-- ci: expect s: exegete <version> -->\n"
        '<!-- ci: run s: echo "exegete 0.15.1a1" -->\n'
        "<!-- ci: expect s: exegete <version> -->\n"
        '<!-- ci: run s: echo "exegete (pyproject.toml)" -->\n'
        "<!-- ci: expect s: exegete <version> -->\n\n"
        "<!-- ci: run s -->\n```bash\n"
        'echo "$HOME/x"\n# Example output: ~/x\n'
        'echo "/home/$(id -un)/y"\n# Example output: /home/yourname/y\n'
        "true\n# Example output: yourname\n"
        "echo hello\n# Example output: goodbye\n```\n")
    lines = text.split("\n")
    versions = [number for number, line in enumerate(lines, 1)
                if line == "<!-- ci: expect s: exegete <version> -->"]
    [outcome] = _run(tmp_path, text)
    assert sorted((failure.split(":")[0], int(failure.split(":")[1]))
                  for failure in outcome.failures) == [
        ("guide.md", versions[0]), ("guide.md", versions[2]),
        ("guide.md", _at(text, "# Example output: yourname")),
        ("guide.md", _at(text, "# Example output: goodbye"))]


# Stand-ins for a program that keeps running, and what ends each
STAND_INS = {
    "good": ("print('ready', flush=True)\ntime.sleep(600)", "one Ctrl+C"),
    "early": ("print('done', flush=True)", "itself"),
    "traceback": ("print('Traceback (most recent call last):', flush=True)"
                  "\ntime.sleep(600)", "one Ctrl+C"),
    # lets the first Ctrl+C pass, as Exegete started by hand does today
    "stubborn": ("signal.signal(signal.SIGINT, lambda *_: None)\n"
                 "print('ready', flush=True)\ntime.sleep(600)",
                 "closing the terminal"),
    "deaf": ("signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
             "signal.signal(signal.SIGHUP, signal.SIG_IGN)\n"
             "print('ready', flush=True)\ntime.sleep(600)", "a kill"),
}


@needs_bash
def test_a_waiting_program_is_stopped_with_ctrl_c(tmp_path, monkeypatch,
                                                  capsys):
    times = {"QUIET_SECONDS": 1, "SETTLE_SECONDS": 10, "STOP_SECONDS": 2,
             "CLOSE_SECONDS": 2}
    for name, seconds in times.items():
        monkeypatch.setattr(doc_commands, name, seconds)
    for name in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(name, raising=False)
    commands = {}
    for name, (body, _) in STAND_INS.items():
        # never named as a module of the standard library: a script's
        # folder comes first when Python imports `traceback` to print one
        program = tmp_path / f"stand_in_{name}.py"
        program.write_text(f"import signal, time\n{body}\n")
        commands[name] = f"python3 {program}"
    text = ("```bash\n" + "\n".join(commands.values()) + "\n```\n\n" + "".join(
        f"<!-- ci: run {name} waits: {command} -->\n"
        for name, command in commands.items())
        + "<!-- ci: expect good: ready -->\n")
    outcomes, took = [], {}
    for session in doc_commands.read_sessions("guide.md", text):
        started = time.monotonic()
        outcomes += doc_commands.run_sessions(
            [session], tmp_path / session.name, str(REPO))
        took[session.name] = time.monotonic() - started
    for outcome in outcomes:
        name = outcome.session.name
        assert outcome.ended_by == STAND_INS[name][1], (name, outcome)
        mark = _at(text, f"<!-- ci: run {name} waits: {commands[name]} -->")
        assert all(failure.startswith(f"guide.md:{mark}: ")
                   for failure in outcome.failures), outcome.failures
        assert bool(outcome.failures) is (name != "good"), outcome.failures
    # never held past the Ctrl+C's wait, the terminal's and a margin
    limit = sum(times.values()) - times["SETTLE_SECONDS"] + 8
    assert took["stubborn"] < limit and took["deaf"] < limit, took
    doc_commands.report(outcomes, str(REPO))
    rows = capsys.readouterr().out.splitlines()
    for name, (_, ended_by) in STAND_INS.items():
        row = next(row for row in rows if row.startswith(f"| guide.md | {name} |"))
        assert ended_by in row, row
