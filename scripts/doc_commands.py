#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Run the commands the documents mark, and check what they print (v0.15.2).

    python scripts/doc_commands.py --list                 the steps, nothing run
    python scripts/doc_commands.py --run --scratch DIR    each session run

A command takes part when its author marks it with an HTML comment on a
line of its own, which GitHub does not show, at the indentation of its
block, between blocks and paragraphs:

    <!-- ci: run S -->            on the line above a bash block: the block
    <!-- ci: run S: COMMAND -->   one command, found word for word between
                                  the mark and the heading above it
    <!-- ci: run S waits -->      a program that keeps running: the block's
                                  last command line, or `: COMMAND` after it
    <!-- ci: expect S: TEXT -->   TEXT in what the session's last step printed

A `# Example output: TEXT` line in a marked block expects TEXT of the lines
above it, back to the block's start or the previous such line. S names a
session, or several separated by commas. A session is one document's marks
of one name, in document order, run as one bash script that starts with
`cd ~`, so `cd` and `source` carry over. A step is one mark's command or
block, or the part of a block before an example line; the script prints a
line of its own before each, and an expectation is matched against its own
step's output, both streams read in order. A waiting program ends its
session: only its session's expectations may follow it.

Before a command runs, Exegete's clone address in `git clone` becomes this
checkout, named `exegete` as the address names it; the requirement
`exegete` of `pip install`, `pipx install` and `uv tool install` becomes
this checkout, so every session installs this commit; and a line
`export EXEGETE_PROJECT_PATH=` is left out, as QUICKSTART tells a reader
with no project to do. In an expectation, `<version>` is a version number,
`~` and `/Users/yourname` are the session's home, and `yourname` is the
account's name.

Each session has a new home, temporary folder and uv cache under DIR, with
a Documents folder in the home, the check for new versions off, and no
other setting of the caller's: its PATH is the home's `.local/bin`, then a
folder of links to the caller's python3, pipx and uv, then /usr/bin and
/bin, so the only `exegete` it can find is one it installed. A waiting
program runs with a terminal on its standard input. It must print, fall
quiet for 5 seconds within 60, still be running, show no Traceback or
error line, and stop within 10 seconds of one Ctrl+C; 10 seconds after the
Ctrl+C the terminal closes, 5 seconds later the program is killed, and the
summary says which of the three ended it.

Every Markdown file `git ls-files '*.md'` lists is read, test content under
tests/fixtures/ aside. A mark the script cannot run fails with its file and
line. Exits 1 on any failure, 2 when it cannot start. Standard library
only; `--run` needs bash and a terminal, so Linux or macOS.
"""

import argparse
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
SKIPPED = ("tests/fixtures/",)
TOOLS = ("python3", "pipx", "uv")
SESSION_SECONDS = 10 * 60    # one session's limit, so a hang ends
QUIET_SECONDS = 5            # a waiting program has settled...
SETTLE_SECONDS = 60          # ...within this
STOP_SECONDS = 10            # one Ctrl+C stops it within this
CLOSE_SECONDS = 5            # then the terminal closes, then a kill
BAD_LINES = ("Traceback", " - ERROR - ", "Error:")

MARK = re.compile(r"^(?P<indent>[ \t]*)<!--\s*ci:\s*(?P<body>.*?)\s*-->\s*$")
LIKE_A_MARK = re.compile(r"^\s*<!--\s*ci\b")
NAMES = r"(?P<names>[a-z][a-z0-9-]*(?:\s*,\s*[a-z][a-z0-9-]*)*)"
RUN = re.compile(r"run\s+" + NAMES + r"(?P<waits>\s+waits)?"
                 r"(?:\s*:\s*(?P<command>\S.*))?")
EXPECT = re.compile(r"expect\s+" + NAMES + r"\s*:\s*(?P<text>\S.*)")
FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})\s*"
                   r"(?P<info>[^\s`]*)")
HEADING = re.compile(r"^ {0,3}#{1,6}(?:\s|$)")
EXAMPLE = re.compile(r"^\s*#\s*Example output:\s*(?P<text>\S.*?)\s*$")

# What a command becomes before it runs, each with its reason (above)
CLONE = re.compile(r"(?P<lead>\bgit\s+clone\s+)"
                   r"https://github\.com/(?:nicotem|<you>)/exegete\.git"
                   r"(?=\s|$)")
INSTALL = re.compile(r"(?P<lead>\b(?:pipx|uv\s+tool|pip)\s+install"
                     r"(?:\s+--?[\w-]+)*\s+)(?P<quote>[\"']?)exegete"
                     r"(?P<extras>\[[\w,-]+\])?(?P=quote)(?=\s|$)")
PROJECT_LINE = re.compile(r"^\s*export\s+EXEGETE_PROJECT_PATH=")
# A version as `exegete --version` prints it: Python's normal form
VERSION = r"\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?(?!\w)"


class BadMark(Exception):
    """A mark the script cannot run, named by its file and line."""

    def __init__(self, file: str, line: int, reason: str):
        super().__init__(f"{file}:{line}: {reason}")


@dataclass
class Step:
    file: str
    line: int
    command: str
    waits: bool = False
    expects: List[Tuple[int, str]] = field(default_factory=list)


@dataclass
class Session:
    file: str
    name: str
    steps: List[Step] = field(default_factory=list)

    @property
    def folder(self) -> str:
        return f"{self.file[:-3].replace('/', '-')}-{self.name}"


def _closes(fence: str, line: str) -> bool:
    return re.fullmatch(r"[ \t]*" + re.escape(fence[0]) + "{%d,}[ \t]*"
                        % len(fence), line) is not None


def _is_command(line: str) -> bool:
    return bool(line.strip()) and not line.lstrip().startswith("#")


def _block_steps(file: str, lines: List[str], index: int, indent: str,
                 waits: bool) -> List[Step]:
    """The steps of the bash block on the line below the mark at `index`."""
    where = index + 1
    opened = FENCE.match(lines[index + 1]) if index + 1 < len(lines) else None
    if not opened:
        raise BadMark(file, where, "a run mark without a command sits on the "
                                   "line above a bash block")
    if opened.group("info") != "bash":
        raise BadMark(file, where, "the block below the mark is "
                      f"`{opened.group('info') or 'unnamed'}`, not bash")
    if opened.group("indent") != indent:
        raise BadMark(file, where, "the mark's indentation differs from "
                                   "its block's")
    margin, body = len(indent), []
    for line in lines[index + 2:]:
        if _closes(opened.group("fence"), line):
            break
        body.append(line[margin:] if not line[:margin].strip()
                    else line.lstrip())
    commands = [at for at, line in enumerate(body) if _is_command(line)]
    if not commands:
        raise BadMark(file, where, "the block below the mark holds no command")
    steps: List[Step] = []
    part: List[Tuple[int, str]] = []

    def close():
        if any(_is_command(line) for _, line in part):
            kept = [index for index, (_, line) in enumerate(part)
                    if line.strip()]
            lines = part[kept[0]:kept[-1] + 1]
            steps.append(Step(file, lines[0][0],
                              "\n".join(line for _, line in lines)))
        part.clear()

    for offset, line in enumerate(body):
        number = index + 3 + offset
        example = EXAMPLE.match(line)
        if example:
            close()
            if not steps:
                raise BadMark(file, number, "an example line with no command "
                                            "above it in its block")
            steps[-1].expects.append((number, example.group("text")))
        elif waits and offset == commands[-1]:
            close()
            steps.append(Step(file, number, line.strip(), waits=True))
        else:
            part.append((number, line))
    close()
    return steps


def read_sessions(file: str, text: str) -> List[Session]:
    """The sessions one document's marks make, each in document order."""
    lines = text.split("\n")
    sessions: Dict[str, Session] = {}
    waited = set()
    heading, fence = 0, None
    for index, line in enumerate(lines):
        if fence:
            fence = None if _closes(fence, line) else fence
            continue
        opened = FENCE.match(line)
        if opened:
            fence = opened.group("fence")
            continue
        if HEADING.match(line):
            heading = index + 1
        if not LIKE_A_MARK.match(line):
            continue
        where, mark = index + 1, MARK.match(line)
        body = mark.group("body") if mark else ""
        run, expect = RUN.fullmatch(body), EXPECT.fullmatch(body)
        if not (run or expect):
            raise BadMark(file, where, "not a mark this script reads: `run S`, "
                          "`run S: COMMAND`, `run S waits`, `run S waits: "
                          "COMMAND` or `expect S: TEXT`, on one line")
        names = re.split(r"\s*,\s*", (run or expect).group("names"))
        if "waits" in names:
            raise BadMark(file, where, "a session cannot be named `waits`")
        if expect:
            for name in names:
                if name not in sessions:
                    raise BadMark(file, where, "an expectation with no step "
                                  f"before it in session `{name}`")
                sessions[name].steps[-1].expects.append(
                    (where, expect.group("text")))
            continue
        for name in names:
            if name in waited:
                raise BadMark(file, where, f"a run mark after session "
                              f"`{name}`'s waiting program, which ends it")
        waits = bool(run.group("waits"))
        if run.group("command"):
            command = run.group("command")
            above = " ".join(" ".join(
                part for part in lines[heading:index]
                if not LIKE_A_MARK.match(part)).split())
            if " ".join(command.split()) not in above:
                raise BadMark(file, where, f"`{command}` is not found between "
                              "the mark and the heading above it")
            made = [Step(file, where, command, waits)]
        else:
            made = _block_steps(file, lines, index, mark.group("indent"),
                                waits)
        for name in names:
            sessions.setdefault(name, Session(file, name)).steps.extend(
                Step(step.file, step.line, step.command, step.waits,
                     list(step.expects)) for step in made)
            if waits:
                waited.add(name)
    return list(sessions.values())


def tracked_markdown(root: Path) -> List[str]:
    """The Markdown files git tracks, test content aside."""
    result = subprocess.run(
        ["git", "-c", "core.quotepath=off", "ls-files", "-z", "--", "*.md"],
        cwd=str(root), capture_output=True, check=False)
    if result.returncode != 0:
        raise OSError("git ls-files failed: "
                      + result.stderr.decode("utf-8", "replace").strip())
    return sorted(name for name in result.stdout.decode("utf-8").split("\0")
                  if name and not name.startswith(SKIPPED))


def read_all(root: Path) -> Tuple[List[Session], List[str]]:
    """(Every session the tracked documents mark, every bad mark)."""
    sessions, bad = [], []
    for name in tracked_markdown(root):
        text = (root / name).read_text(encoding="utf-8")
        try:
            sessions.extend(read_sessions(name, text))
        except BadMark as error:
            bad.append(str(error))
    return sessions, bad


def substitute(command: str, checkout: str) -> str:
    """The command as it runs: this checkout for Exegete's clone address
    and for its requirement, and the project's line left out."""
    place = shlex.quote(checkout)
    lines = []
    for line in command.split("\n"):
        if PROJECT_LINE.match(line):
            continue

        def clone(found, line=line):
            rest = line[found.end():].strip()
            named = not rest or rest.startswith("#")
            return found.group("lead") + place + (" exegete" if named else "")

        line = CLONE.sub(clone, line)
        line = INSTALL.sub(lambda found: found.group("lead") + shlex.quote(
            checkout + (found.group("extras") or "")), line)
        lines.append(line)
    return "\n".join(lines)


def expectation(text: str, home: str, account: str) -> "re.Pattern[str]":
    """An expectation as a pattern: its words as written, `<version>` a
    version number, `~` and `/Users/yourname` the home, `yourname` the
    account's name."""
    read = {"<version>": VERSION, "/Users/yourname": re.escape(home),
            "~": re.escape(home), "yourname": re.escape(account)}
    return re.compile("".join(
        read.get(part, re.escape(part)) for part in
        re.split(r"(<version>|/Users/yourname|~|yourname)", text)))


@dataclass
class Outcome:
    session: Session
    outputs: List[Optional[str]]     # each step's, None when not reached
    failures: List[str]
    ended_by: Optional[str] = None   # what ended its waiting program
    seconds: float = 0.0


def scratch_problem(scratch: Path) -> Optional[str]:
    """Why the folder cannot hold the sessions, or None."""
    homes = [Path(os.path.expanduser("~"))]
    try:
        import pwd
        homes.append(Path(pwd.getpwuid(os.getuid()).pw_dir))
    except (ImportError, KeyError):
        pass
    where = scratch.resolve()
    if where in [home.resolve() for home in homes]:
        return f"{scratch} is the home folder"
    if where.exists() and (not where.is_dir() or any(where.iterdir())):
        return f"{scratch} is neither new nor empty"
    return None


def _cut(token: str, what: str) -> str:
    return f"@@doc-commands {token} {what}@@"


def session_script(session: Session, token: str, checkout: str,
                   watcher: str) -> str:
    lines = ["set -eo pipefail", "exec 2>&1", "cd ~"]
    for number, step in enumerate(session.steps, 1):
        lines.append("printf '%s\\n' "
                     + shlex.quote(_cut(token, f"step {number}")))
        command = substitute(step.command, checkout)
        lines.append(f"exec {watcher} {shlex.quote('--watch=' + command)}"
                     if step.waits else command)
    return "\n".join(lines) + "\n"


def run_session(session: Session, scratch: Path, tools: Path, checkout: str,
                token: str) -> Outcome:
    """Run one session in a new home of its own, and judge each step."""
    folder = scratch / session.folder
    home, tmp, cache = folder / "home", folder / "tmp", folder / "uv-cache"
    for path in (home / "Documents", tmp, cache):
        path.mkdir(parents=True)
    result = folder / "waiting.json"
    times = (QUIET_SECONDS, SETTLE_SECONDS, STOP_SECONDS, CLOSE_SECONDS)
    watcher = " ".join(shlex.quote(part) for part in (
        sys.executable, str(Path(__file__).resolve()), "--result",
        str(result), "--cut", _cut(token, "after ctrl-c"),
        "--times", ",".join(f"{seconds:g}" for seconds in times)))
    script = folder / "session.sh"
    script.write_text(session_script(session, token, checkout, watcher),
                      encoding="utf-8")
    environment = {
        "HOME": str(home), "USERPROFILE": str(home), "TMPDIR": str(tmp),
        "UV_CACHE_DIR": str(cache), "EXEGETE_UPDATE_CHECK": "off",
        "LANG": "C.UTF-8", "PATH": os.pathsep.join(
            (str(home / ".local" / "bin"), str(tools), "/usr/bin", "/bin"))}
    output, late, started = folder / "output.txt", False, time.monotonic()
    with open(output, "wb") as handle:
        process = subprocess.Popen(
            [shutil.which("bash") or "/bin/bash", "--noprofile", "--norc",
             str(script)], stdin=subprocess.DEVNULL, stdout=handle,
            stderr=subprocess.STDOUT, env=environment, cwd=str(home),
            start_new_session=True)
        try:
            code = process.wait(timeout=SESSION_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            code, late = process.wait(), True
    outputs = step_outputs(output.read_text(encoding="utf-8",
                                            errors="replace"),
                           token, len(session.steps))
    failures, ended_by = judge(session, outputs, code, late, result,
                               str(home), _cut(token, "after ctrl-c"))
    return Outcome(session, outputs, failures, ended_by,
                   time.monotonic() - started)


def step_outputs(text: str, token: str, count: int) -> List[Optional[str]]:
    """Each step's output, cut at the script's own lines; None for a step
    the session did not reach."""
    found = [re.search("^" + re.escape(_cut(token, f"step {number}")) + "$",
                       text, re.M) for number in range(1, count + 1)]
    outputs: List[Optional[str]] = []
    for number, cut in enumerate(found):
        later = [after.start() for after in found[number + 1:] if after]
        outputs.append(text[cut.end() + 1:later[0] if later else len(text)]
                       if cut else None)
    return outputs


def judge(session: Session, outputs: List[Optional[str]], code: int,
          late: bool, result: Path, home: str,
          after_ctrl_c: str) -> Tuple[List[str], Optional[str]]:
    """(The session's failures, each with its file and line, and what
    ended its waiting program). The step the session stopped in failed;
    each expectation is read in its own step's output alone, a waiting
    program's in what it printed before the Ctrl+C."""
    reached = [number for number, out in enumerate(outputs) if out is not None]
    failures: List[str] = []
    ended_by = None
    if not reached:
        failures.append(f"{session.file}:{session.steps[0].line}: the session "
                        f"failed before its first step (exit code {code})")
    for number, (step, out) in enumerate(zip(session.steps, outputs)):
        if out is None:
            continue
        if step.waits:
            out = out.split(after_ctrl_c)[0]
            try:
                watched = json.loads(result.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                watched = {"ended_by": None,
                           "problems": ["its watch gave no result"]}
            ended_by = watched["ended_by"]
            failures.extend(f"{step.file}:{step.line}: `{step.command}`: "
                            f"{problem}" for problem in watched["problems"])
        elif number == reached[-1] and (late or code != 0):
            failures.append(f"{step.file}:{step.line}: " + (
                f"the session ran past its {SESSION_SECONDS // 60} minutes "
                "in this step" if late else
                f"this step failed with exit code {code}"))
            continue
        elif number == reached[-1] and number + 1 < len(session.steps):
            failures.append(f"{step.file}:{step.line}: the session ended "
                            "after this step, before the rest")
        for line, words in step.expects:
            if not expectation(words, home, _account()).search(out):
                failures.append(f"{step.file}:{line}: `{words}` is not in "
                                f"what the step at line {step.line} printed")
    return failures, ended_by


def _account() -> str:
    import pwd
    return pwd.getpwuid(os.geteuid()).pw_name


def run_sessions(sessions: List[Session], scratch: Path,
                 checkout: str) -> List[Outcome]:
    """Run each session in a new home under `scratch`."""
    problem = scratch_problem(scratch)
    if problem:
        raise ValueError(problem)
    tools = scratch.resolve() / "tools"
    tools.mkdir(parents=True)
    for name in TOOLS:
        if shutil.which(name):
            (tools / name).symlink_to(shutil.which(name))
        else:
            print(f"{name} is not installed here: a session that runs it "
                  "fails, naming it", flush=True)
    token, outcomes = secrets.token_hex(8), []
    for session in sessions:
        print(f"{session.file}, session `{session.name}`: running", flush=True)
        outcomes.append(run_session(session, scratch.resolve(), tools,
                                    checkout, token))
    return outcomes


def watch(command: str, result: Path, cut: str,
          times: Tuple[float, float, float, float]) -> int:
    """Start a waiting program as a terminal does and stop it with one
    Ctrl+C: 0 when it settled cleanly and one Ctrl+C stopped it, else 1.
    Its output follows on standard output once it has ended, what came
    after the Ctrl+C behind `cut`; what happened goes to `result`."""
    import fcntl
    import termios
    quiet, settle, stop, close = times
    request = getattr(termios, "TIOCSCTTY", None)

    def as_in_a_terminal():
        # A program started from a background job inherits SIGINT and
        # SIGQUIT ignored (SIGHUP too under nohup); one started in a
        # terminal has the defaults, and the terminal as its own
        for number in (signal.SIGINT, signal.SIGQUIT, signal.SIGHUP,
                       signal.SIGTERM):
            signal.signal(number, signal.SIG_DFL)
        if request is not None:
            fcntl.ioctl(0, request, 0)

    log = result.with_name(result.stem + "-output.txt")
    master, slave = os.openpty()
    with open(log, "wb") as handle:
        program = subprocess.Popen(
            ["bash", "-c", command], stdin=slave, stdout=handle,
            stderr=subprocess.STDOUT, start_new_session=True,
            preexec_fn=as_in_a_terminal)
    os.close(slave)
    problems: List[str] = []
    started = changed = time.monotonic()
    size = 0
    while program.poll() is None:
        now = time.monotonic()
        if log.stat().st_size != size:
            size, changed = log.stat().st_size, now
        if (size and now - changed >= quiet) or now - started >= settle:
            break
        time.sleep(0.05)
    before = log.read_bytes()
    if program.poll() is not None:
        ended_by = "itself"
        problems.append("it ended by itself before the Ctrl+C ("
                        + _status(program.returncode) + ")")
    else:
        if not before:
            problems.append(f"it printed nothing within {settle:g} seconds")
        elif time.monotonic() - changed < quiet:
            problems.append(f"it did not fall quiet for {quiet:g} seconds "
                            f"within {settle:g}")
        problems.extend(f"it printed `{bad.strip()}`" for bad in BAD_LINES
                        if bad in before.decode("utf-8", "replace"))
        os.killpg(program.pid, signal.SIGINT)
        if _ends(program, stop):
            ended_by = "one Ctrl+C"
        else:
            os.close(master)
            master = -1
            ended_by = ("closing the terminal" if _ends(program, close)
                        else "a kill")
            problems.append(f"it did not stop within {stop:g} seconds of one "
                            f"Ctrl+C; {ended_by} ended it")
    try:
        os.killpg(program.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    program.wait()
    if master >= 0:
        os.close(master)
    written = log.read_bytes()
    out = sys.stdout.buffer
    out.write(before + (b"\n" if before and not before.endswith(b"\n")
                        else b""))
    out.write(cut.encode("utf-8") + b"\n" + written[len(before):])
    out.flush()
    result.write_text(json.dumps({"ended_by": ended_by,
                                  "problems": problems}), encoding="utf-8")
    return 0 if ended_by == "one Ctrl+C" and not problems else 1


def _ends(program: subprocess.Popen, seconds: float) -> bool:
    try:
        program.wait(timeout=seconds)
        return True
    except subprocess.TimeoutExpired:
        return False


def _status(code: int) -> str:
    return (f"signal {signal.Signals(-code).name}" if code < 0
            else f"exit code {code}")


def show(sessions: List[Session]) -> None:
    for session in sessions:
        print(f"{session.file}, session `{session.name}`")
        for number, step in enumerate(session.steps, 1):
            kind = "waits" if step.waits else "runs"
            print(f"  step {number}, line {step.line}, {kind}:")
            for line in substitute(step.command, "<checkout>").split("\n"):
                print(f"    {line}")
            for line, words in step.expects:
                print(f"  expects, line {line}: {words}")


def _annotate(failure: str) -> None:
    """An error annotation on the line, under GitHub Actions."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    place, _, message = failure.partition(": ")
    file, _, line = place.partition(":")
    message = message.replace("%", "%25").replace("\n", "%0A")
    print(f"::error file={file},line={line or 1},"
          f"title=the documents' commands::{message}")


def report(outcomes: List[Outcome], checkout: str) -> int:
    """Each step's command and output, the failures, and one table."""
    rows = ["| document | session | steps run | minutes | result |",
            "|---|---|---|---|---|"]
    for outcome in outcomes:
        session = outcome.session
        print(f"\n=== {session.file}, session `{session.name}`")
        for number, (step, out) in enumerate(
                zip(session.steps, outcome.outputs), 1):
            print(f"--- step {number}, {session.file}:{step.line}")
            for line in substitute(step.command, checkout).split("\n"):
                print(f"$ {line}")
            print(out.rstrip("\n") if out is not None else "(not reached)")
        for failure in outcome.failures:
            print(f"FAILED {failure}")
            _annotate(failure)
        result = (outcome.failures[0] if outcome.failures else "passed")
        if outcome.ended_by:
            result += f"; its waiting program was ended by {outcome.ended_by}"
        reached = sum(out is not None for out in outcome.outputs)
        rows.append(f"| {session.file} | {session.name} | {reached} of "
                    f"{len(session.steps)} | {outcome.seconds / 60:.1f} | "
                    f"{result.replace('|', '/')} |")
    print("\n" + "\n".join(rows))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a",
                  encoding="utf-8") as handle:
            handle.write("### The documents' commands\n\n"
                         + "\n".join(rows) + "\n")
    return 1 if any(outcome.failures for outcome in outcomes) else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the commands the documents mark, each set in a new "
                    "home, and check what they print.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true",
                      help="print each session's steps and expectations, "
                           "and run nothing")
    mode.add_argument("--run", action="store_true",
                      help="run each session in a new home under --scratch")
    mode.add_argument("--watch", help=argparse.SUPPRESS)
    parser.add_argument("--scratch", type=Path,
                        help="a new or empty folder for the sessions' homes")
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--cut", help=argparse.SUPPRESS)
    parser.add_argument("--times", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.watch is not None:
        times = tuple(float(seconds) for seconds in args.times.split(","))
        return watch(args.watch, args.result, args.cut, times)
    if args.run and args.scratch is None:
        parser.error("--run needs --scratch")
    try:
        sessions, bad = read_all(REPO)
    except OSError as error:
        print(f"doc_commands.py: {error}", file=sys.stderr)
        return 2
    for problem in bad:
        print(problem)
        _annotate(problem)
    if bad:
        return 1
    if not sessions:
        print("No document marks a command, so nothing was checked: has the "
              "marks' form changed?")
        return 1
    if args.list:
        show(sessions)
        return 0
    if os.name == "nt" or not shutil.which("bash"):
        print("doc_commands.py: --run needs bash and a terminal (Linux or "
              "macOS)", file=sys.stderr)
        return 2
    try:
        outcomes = run_sessions(sessions, args.scratch, str(REPO))
    except ValueError as error:
        print(f"doc_commands.py: {error}", file=sys.stderr)
        return 2
    return report(outcomes, str(REPO))


if __name__ == "__main__":
    sys.exit(main())
