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


# v0.14.1, the AI coder name file: after Exegete has moved a project's
# name into exegete.json, the real 0.14.0 finds its qualcoder_mcp.json
# marked, reports it as written by a newer version and refuses both to
# write it and to write any row under its name. The same holds once a
# mark that failed has been made by the write path's retry.
REFUSAL = r"""
import json, pathlib, sys
folder = pathlib.Path(sys.argv[1])
import qualcoder_mcp, qualcoder_mcp.server as server
from qualcoder_mcp import project_settings as ps
out = {"module": qualcoder_mcp.__file__, "version": qualcoder_mcp.__version__}
state = ps.read_sidecar(folder)
out["status"] = state.status
out["name_read"] = state.name
if sys.argv[2] == "write":
    try:
        ps.write_ai_coder_name(folder, "Written By 0.14")
        out["write"] = "written"
    except ps.SidecarWriteError as e:
        out["write"] = str(e)
server.current_project_path = str(folder / "data.qda")
owner, refusal = server._resolve_write_owner()
out["owner"] = owner
out["refusal"] = (refusal or {}).get("error")
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def run_0140(tmp_path_factory):
    """The published 0.14.0a0 in an environment of its own, and a way to
    run the refusal script with it against a project folder."""
    house = os.environ.get(rh.WHEELHOUSE)
    if not house or not list(Path(house).glob("qualcoder_mcp-0.14.0a0-*")):
        rh.skip_or_fail(f"{rh.WHEELHOUSE} does not hold the published "
                        f"qualcoder_mcp 0.14.0a0 wheel")
    base = tmp_path_factory.mktemp("proof0140")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PIP_", "QUALCODER", "EXEGETE", "PYTHON"))}
    venv = base / "v0140"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                   env=env, timeout=240)
    python = venv / BIN / f"python{EXE}"
    subprocess.run([str(python), "-m", "pip", "install", "--no-index",
                    "--find-links", house, "qualcoder-mcp==0.14.0a0"],
                   check=True, env=env, capture_output=True, timeout=240)
    script = base / "refusal.py"
    script.write_text(REFUSAL, encoding="utf-8")

    def run(folder: Path, mode: str = "write") -> dict:
        home = folder.parent
        run_env = dict(env, HOME=str(home), USERPROFILE=str(home),
                       PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([str(python), "-B", str(script), str(folder),
                               mode], capture_output=True, text=True,
                              encoding="utf-8", env=run_env, cwd=str(base),
                              timeout=240)
        assert proc.returncode == 0, proc.stderr[-3000:]
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        assert out["version"] == "0.14.0a0"
        assert Path(out["module"]).resolve().is_relative_to(venv.resolve())
        return out

    return run


def project_as_0140_left_it(tmp_path: Path, name: str = "Before") -> Path:
    """A project folder whose qualcoder_mcp.json 0.14.0 wrote."""
    from exegete import project_settings as ps
    folder = tmp_path / "home" / "Study.qda"
    folder.mkdir(parents=True)
    (folder / "data.qda").write_bytes(b"")
    (folder / ps.OLD_SIDECAR_NAME).write_text(json.dumps({
        "format": "qualcoder-mcp-project", "format_version": 1,
        "ai_coder_name": {"name": name, "set_at": None, "note": "",
                          "host_declaration": None},
        "ai_coder_name_history": []}), encoding="utf-8")
    return folder


def assert_0140_refuses(out: dict, name_read):
    assert out["status"] == "newer_format"
    assert out["name_read"] == name_read
    assert "written by a newer version" in out["write"]
    assert out["owner"] is None
    assert "written by a newer version" in out["refusal"]


def test_the_published_0140_refuses_the_marked_file(tmp_path, run_0140):
    from exegete import project_settings as ps
    folder = project_as_0140_left_it(tmp_path)
    ps.write_ai_coder_name(folder, "After")         # one change by Exegete
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert_0140_refuses(run_0140(folder), "Before")
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert ps.read_sidecar(folder).name == "After"


def test_the_published_0140_refuses_once_a_failed_mark_is_retried(
        tmp_path, run_0140, monkeypatch):
    # The first change of name cannot mark the earlier file (a replace
    # that fails for it alone, as a locked file's does): 0.14.0 still
    # writes under the old name. Exegete's next owner-bearing write
    # retries the mark, and 0.14.0 then refuses.
    import exegete.server as server
    from exegete import project_settings as ps
    folder = project_as_0140_left_it(tmp_path)
    real = ps.os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == ps.OLD_SIDECAR_NAME:
            raise PermissionError(13, "Operation not permitted", str(dst))
        return real(src, dst, *args, **kwargs)

    monkeypatch.setattr(ps.os, "replace", replace)
    stored = ps.store_ai_coder_name(folder, "After")
    assert stored.earlier.status == ps.EARLIER_NOT_MARKED
    out = run_0140(folder, mode="read")
    assert (out["status"], out["owner"]) == ("project", "Before")
    monkeypatch.setattr(ps.os, "replace", real)
    monkeypatch.setattr(server, "current_project_path",
                        str(folder / "data.qda"))
    assert server._resolve_write_owner() == ("After", None)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert_0140_refuses(run_0140(folder), "Before")
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert ps.read_sidecar(folder).name == "After"


def test_the_published_0140_refuses_a_project_exegete_named_first(
        tmp_path, run_0140):
    # No qualcoder_mcp.json before: Exegete writes one already marked,
    # holding no name, so 0.14.0 refuses and says to upgrade rather than
    # ask for a name of its own and write under it beside Exegete.
    from exegete import project_settings as ps
    folder = tmp_path / "home" / "Study.qda"
    folder.mkdir(parents=True)
    (folder / "data.qda").write_bytes(b"")
    ps.write_ai_coder_name(folder, "Named By Exegete")
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert sorted(before) == ["data.qda", ps.SIDECAR_NAME,
                              ps.OLD_SIDECAR_NAME]
    assert_0140_refuses(run_0140(folder), None)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert ps.read_sidecar(folder).name == "Named By Exegete"
