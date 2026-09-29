# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: the real 0.14.0 works through the link.

After the move, a copy of the server still on 0.14 on the same computer
(a second host, the owner's own entry during the change-over) finds
~/.qualcoder_mcp as a link to ~/.exegete (a junction on Windows). This
runs the published qualcoder-mcp 0.14.0a0 in a home folder of its own,
set up exactly so, with a key already moved: it issues a preview token
and verifies it, saves, lists and loads a session, writes the
last-project hint and reads it back, and runs an export's folder check.
Everything must land inside ~/.exegete, the link must still be a link,
and the key must be unchanged.

Slow, and offline: it installs 0.14.0a0 and its dependencies from the
folder RENAME_TEST_WHEELHOUSE names (CI's rename job fills it with
`pip download`, the published 0.14.0a0 wheel included), and is skipped
without one.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import rename_helpers as rh

sys.path.insert(0, str(rh.REPO / "src"))
from exegete import state_folder                  # noqa: E402

pytestmark = pytest.mark.slow

BIN = "Scripts" if os.name == "nt" else "bin"
EXE = ".exe" if os.name == "nt" else ""
KEY = "5e" * 32

PROOF = r'''
import json, pathlib, sys
home = pathlib.Path(sys.argv[1])
project = home / "Study.qda" / "data.qda"
import qualcoder_mcp, qualcoder_mcp.server as server
from qualcoder_mcp import preview_tokens
from qualcoder_mcp.sessions import AICodingSession
out = {"module": qualcoder_mcp.__file__,
       "version": qualcoder_mcp.__version__,
       "state_home": str(preview_tokens.STATE_HOME)}
args = {"source_id": 1, "target_id": 2}
token = preview_tokens.issue("merge_codes", args, str(project), "state")
out["token_verifies"] = preview_tokens.verify(
    token, "merge_codes", args, str(project), "state") == preview_tokens.OK
session = AICodingSession(project_path=str(project), description="proof")
server.session_manager.save_session(session)
out["session_id"] = session.session_id
out["session_listed"] = any(
    s["coding_session_id"] == session.session_id
    for s in server.session_manager.list_sessions())
out["session_loaded"] = server.session_manager.load_session(
    session.session_id).session_id == session.session_id
server._remember_mru_project(str(project))
out["hint"] = str(project) in server._mru_hint()
out["export_refused_old"] = server._inside_state_home(
    home / ".qualcoder_mcp" / "x.csv")
out["export_refused_new"] = server._inside_state_home(
    home / ".exegete" / "x.csv")
print(json.dumps(out))
'''


def prepare_home(home: Path) -> Path:
    """~/.exegete holding a moved key, ~/.qualcoder_mcp a link to it (a
    junction on Windows), and a project for the hint to name."""
    new = home / ".exegete"
    new.mkdir(parents=True, mode=0o700)
    secret = new / "preview_secret"
    secret.write_text(KEY + "\n", encoding="ascii")
    if os.name != "nt":
        os.chmod(new, 0o700)
        os.chmod(secret, 0o600)
    state_folder.make_link(new, home / ".qualcoder_mcp")
    project = home / "Study.qda" / "data.qda"
    project.parent.mkdir()
    project.write_bytes(b"")
    return new


def check_proof(home: Path, out: dict):
    """What the proof must show, whichever copy of 0.14.0 ran it."""
    new = home / ".exegete"
    for key in ("token_verifies", "session_listed", "session_loaded",
                "hint", "export_refused_old", "export_refused_new"):
        assert out[key] is True, (key, out)
    assert (new / "sessions" / f"session_{out['session_id']}.json").is_file()
    assert (new / "mru_project.json").is_file()
    assert (new / "preview_secret").read_text(encoding="ascii") == \
        KEY + "\n"
    assert state_folder.is_link(home / ".qualcoder_mcp")
    assert state_folder.same_folder(home / ".qualcoder_mcp", new)
    assert sorted(p.name for p in home.iterdir()) == \
        [".exegete", ".qualcoder_mcp", "Study.qda"]


def test_the_published_0140_through_the_link(tmp_path):
    house = os.environ.get(rh.WHEELHOUSE)
    if not house or not list(Path(house).glob("qualcoder_mcp-0.14.0a0-*")):
        rh.skip_or_fail(f"{rh.WHEELHOUSE} does not hold the published "
                        f"qualcoder_mcp 0.14.0a0 wheel")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PIP_", "QUALCODER", "EXEGETE", "PYTHON"))}
    venv = tmp_path / "v0140"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                   env=env, timeout=240)
    python = venv / BIN / f"python{EXE}"
    subprocess.run([str(python), "-m", "pip", "install", "--no-index",
                    "--find-links", house, "qualcoder-mcp==0.14.0a0"],
                   check=True, env=env, capture_output=True, timeout=240)
    home = tmp_path / "home"
    home.mkdir()
    prepare_home(home)
    script = tmp_path / "proof.py"
    script.write_text(PROOF, encoding="utf-8")
    env.update(HOME=str(home), USERPROFILE=str(home),
               PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([str(python), "-B", str(script), str(home)],
                          capture_output=True, text=True, encoding="utf-8",
                          env=env, cwd=str(tmp_path), timeout=240)
    assert proc.returncode == 0, proc.stderr[-3000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["version"] == "0.14.0a0"
    assert Path(out["module"]).resolve().is_relative_to(venv.resolve())
    check_proof(home, out)
