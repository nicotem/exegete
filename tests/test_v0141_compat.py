# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename: the server's settings under both spellings.

Each setting has a new spelling (EXEGETE_...) and the earlier one, read
until v1.0, through one reader (env_settings). The five cases of each
pair: new only, silent; old only, used and named once in the start-up
log; both equal after the usual tidying, silent; both different, the
server does not start and names the two spellings, never the values;
and a workspace is required if either spelling says 1.

The cases run through `main()` in this process, with the transport
stubbed (as tests/test_v012_cli.py does), which is fast enough to run
all thirty on every platform; a few run in a real subprocess as well,
to prove the process exits and writes what a host keeps.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import exegete.server as server                   # noqa: E402
from exegete import database, env_settings, names  # noqa: E402

SETTINGS = names.SETTINGS

# For each setting: a value, and a second spelling of the same value that
# differs only by the tidying its read does (it must count as equal), and
# a value that differs.
def _values(tmp_path):
    project = tmp_path / "Study.qda"
    project.mkdir(exist_ok=True)
    home = Path.home()                    # the sandbox's
    return {
        "toolset": ("core", " Core ", "full"),
        "ai_coder_name": ("Ann", " Ann ", "Bob"),
        "workspace": (str(home / "work"), "~/work", str(home / "other")),
        "workspace_required": ("1", " 1 ", "0"),
        "allow_unknown_schema": ("1", "1", "0"),
        "project_path": (str(project), str(project),
                         str(tmp_path / "Other.qda")),
    }


def test_the_table_is_six_pairs_with_the_new_prefix():
    assert len(SETTINGS) == 6
    for new, old in SETTINGS.values():
        assert new.startswith(names.ENV_PREFIX) and new != old
        assert old.startswith("QUALCODER_")
    assert {old for _, old in SETTINGS.values()} == {
        "QUALCODER_MCP_TOOLSET", "QUALCODER_MCP_AI_CODER_NAME",
        "QUALCODER_MCP_WORKSPACE", "QUALCODER_MCP_WORKSPACE_REQUIRED",
        "QUALCODER_MCP_ALLOW_UNKNOWN_SCHEMA", "QUALCODER_PROJECT_PATH"}


class TestTheReader:

    @pytest.mark.parametrize("key", sorted(SETTINGS))
    def test_the_five_cases(self, key, tmp_path):
        new, old = SETTINGS[key]
        value, same, other = _values(tmp_path)[key]
        read = env_settings.read
        assert read(key, {}) == (None, new, False, False)
        assert read(key, {new: value}) == (value, new, False, False)
        assert read(key, {old: value}) == (value, old, True, False)
        assert read(key, {new: value, old: same}).conflict is False
        if key == "workspace_required":
            # required if either says 1, never a refusal
            got = read(key, {new: other, old: value})
            assert got.conflict is False and got.value == value
            got = read(key, {new: value, old: other})
            assert got.conflict is False and got.value == value
        else:
            assert read(key, {new: value, old: other}).conflict is True

    def test_a_blank_spelling_counts_as_unset(self):
        new, old = SETTINGS["ai_coder_name"]
        assert env_settings.read("ai_coder_name", {new: " ", old: "Ann"}) \
            == ("Ann", old, True, False)
        # neither says anything: a blank is still handed on, so a blank
        # coder name still stops the server as before
        assert env_settings.read("ai_coder_name", {old: ""}) \
            == ("", old, False, False)

    def test_the_refusal_names_the_spellings_never_the_values(self):
        new, old = SETTINGS["toolset"]
        problems = env_settings.conflicts({new: "core", old: "full"})
        assert len(problems) == 1
        assert new in problems[0] and old in problems[0]
        assert "core" not in problems[0] and "full" not in problems[0]
        assert "until v1.0" in problems[0]

    def test_the_log_line_names_the_new_spelling_and_until_when(self):
        new, old = SETTINGS["project_path"]
        (line,) = env_settings.old_spellings_in_use({old: "/p"})
        assert line.startswith(f"{old} is the earlier spelling of {new}")
        assert "until v1.0" in line


class TestThroughMain:
    """The rules as a start of the server applies them."""

    @pytest.fixture
    def stub_run(self, monkeypatch):
        calls = []
        monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
        monkeypatch.setattr(sys, "stdin", None)
        return calls

    def _start(self, monkeypatch, caplog, env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        caplog.set_level("INFO")
        try:
            server.main([])
        except SystemExit as exc:
            return exc.code
        return 0

    @pytest.mark.parametrize("key", sorted(SETTINGS))
    def test_old_only_is_used_and_named_once(self, key, monkeypatch,
                                             caplog, capsys, stub_run,
                                             tmp_path):
        new, old = SETTINGS[key]
        value = _values(tmp_path)[key][0]
        if key == "workspace_required":
            monkeypatch.setenv(SETTINGS["workspace"][0], str(tmp_path / "w"))
        code = self._start(monkeypatch, caplog, {old: value})
        assert code == 0, capsys.readouterr().err
        lines = [r.getMessage() for r in caplog.records
                 if r.getMessage().startswith(f"{old} is the earlier")]
        assert len(lines) == 1 and new in lines[0]

    @pytest.mark.parametrize("key", sorted(SETTINGS))
    def test_new_only_and_both_equal_are_silent(self, key, monkeypatch,
                                                caplog, capsys, stub_run,
                                                tmp_path):
        new, old = SETTINGS[key]
        value, same, _ = _values(tmp_path)[key]
        if key == "workspace_required":
            monkeypatch.setenv(SETTINGS["workspace"][0], str(tmp_path / "w"))
        for env in ({new: value}, {new: value, old: same}):
            caplog.clear()
            assert self._start(monkeypatch, caplog, env) == 0, \
                capsys.readouterr().err
            assert not [r for r in caplog.records
                        if "earlier spelling" in r.getMessage()]
            for name in env:
                monkeypatch.delenv(name)

    @pytest.mark.parametrize("key", sorted(set(SETTINGS)
                                           - {"workspace_required"}))
    def test_both_different_stop_the_server(self, key, monkeypatch, caplog,
                                            capsys, stub_run, tmp_path):
        new, old = SETTINGS[key]
        value, _, other = _values(tmp_path)[key]
        code = self._start(monkeypatch, caplog, {new: value, old: other})
        err = capsys.readouterr().err
        assert code == 1
        assert f"Error: {new} and {old} are both set" in err
        for given in (value.strip(), other.strip()):
            if len(given) > 1:            # not "1" of "v1.0"
                assert given not in err
        assert stub_run == []

    def test_a_workspace_is_required_if_either_spelling_says_so(
            self, monkeypatch, caplog, capsys, stub_run):
        new, old = SETTINGS["workspace_required"]
        for env in ({new: "1", old: "0"}, {new: "0", old: "1"}):
            code = self._start(monkeypatch, caplog, env)
            assert code == 1
            err = capsys.readouterr().err
            assert "requires a folder for projects" in err
            for name in env:
                monkeypatch.delenv(name)
        assert stub_run == []


def _child_env(home, extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QUALCODER", "EXEGETE"))}
    env.update({"PYTHONPATH": str(REPO / "src"), "HOME": str(home),
                "USERPROFILE": str(home), "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(extra)
    return env


def _run_server(home, extra):
    """Start the server as a host would, with standard input closed at
    once: it starts, finds no host, and exits 0 (or refuses, 1)."""
    return subprocess.run(
        [sys.executable, "-B", "-m", "exegete.server"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
        encoding="utf-8", env=_child_env(home, extra), timeout=120)


class TestInARealProcess:

    def test_two_spellings_that_disagree_stop_it(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        new, old = SETTINGS["toolset"]
        proc = _run_server(home, {new: "core", old: "full"})
        assert proc.returncode == 1
        assert f"Error: {new} and {old} are both set" in proc.stderr
        assert proc.stdout == ""

    def test_an_earlier_spelling_is_used_and_named(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        new, old = SETTINGS["toolset"]
        proc = _run_server(home, {old: "core"})
        assert proc.returncode == 0, proc.stderr
        assert f"{old} is the earlier spelling of {new}" in proc.stderr
        assert "Toolset mode: core" in proc.stderr

    def test_a_message_names_the_spelling_that_was_set(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        for name in SETTINGS["workspace"]:
            proc = _run_server(home, {name: "relative/folder"})
            assert proc.returncode == 1
            assert f"Error: {name} must be a full path" in proc.stderr


class TestTheExtensionSetsBothSpellings:
    """The manifest's `env` sets both spellings of its three settings to
    the same value. Until v1.0, while the earlier spellings are read: a
    setting the manifest names overrides one of the same name inherited
    from the environment, so an old value exported in a shell profile,
    or passed on by the app, can never disagree and stop the extension."""

    TEMPLATE = json.loads((REPO / "packaging" / "desktop-extension" /
                           "manifest.in.json").read_text(encoding="utf-8"))

    def test_the_six_entries_and_their_equality(self):
        env = self.TEMPLATE["server"]["mcp_config"]["env"]
        assert len(env) == 6
        for key in ("toolset", "workspace", "workspace_required"):
            new, old = SETTINGS[key]
            assert env[new] == env[old]
        assert env[SETTINGS["toolset"][0]] == "${user_config.toolset}"

    def test_it_starts_over_stray_old_values(self, tmp_path):
        import smoke_desktop_extension as smoke
        home = tmp_path / "home"
        home.mkdir()
        manifest = dict(self.TEMPLATE, name="qualcoder-mcp",
                        author={"name": "Niccolò Tempini"})
        config = smoke.launch_config(manifest, tmp_path / "ext", {})
        stray = {"QUALCODER_MCP_TOOLSET": "core",
                 "QUALCODER_MCP_WORKSPACE": str(tmp_path / "elsewhere")}
        # the app lays the manifest's env over what it passes on
        proc = _run_server(home, {**stray, **config["env"]})
        assert proc.returncode == 0, proc.stderr
        assert "Toolset mode: lifecycle" in proc.stderr
        assert "earlier spelling" not in proc.stderr


class TestNoOtherEnvironmentRead:
    """Every environment read in the package goes through env_settings:
    the rule looks for READS, not for names, since the reads go through
    constants (a search for literal names would miss them)."""

    ALLOWED = {"env_settings.py": "the reader itself"}

    ENV_NAMES = ("environ", "environb", "getenv", "getenvb")

    @classmethod
    def _reads(cls, source):
        """Every `os.environ`, `os.getenv` and the like, and every use of
        one of them imported from os by name. (A parameter that happens
        to be called `environ`, a mapping passed in, is not a read.)"""
        tree = ast.parse(source)
        imported = {alias.asname or alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                    and node.module in ("os", "posix", "nt")
                    for alias in node.names if alias.name in cls.ENV_NAMES}
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and \
                    node.attr in cls.ENV_NAMES and \
                    isinstance(node.value, ast.Name) and \
                    node.value.id in ("os", "posix", "nt"):
                found.append(f"{ast.unparse(node)} line {node.lineno}")
            elif isinstance(node, ast.Name) and node.id in imported:
                found.append(f"{node.id} line {node.lineno}")
        return found

    def test_none_outside_the_reader(self):
        offenders = {}
        for path in sorted((REPO / "src" / "exegete").glob("*.py")):
            if path.name in self.ALLOWED:
                continue
            reads = self._reads(path.read_text(encoding="utf-8"))
            if reads:
                offenders[path.name] = reads
        assert offenders == {}

    def test_the_check_would_notice(self):
        assert self._reads("import os\nx = os.environ.get('A')\n")
        assert self._reads("import os\nx = os.getenv('A')\n")
        assert self._reads("from os import environ\nx = environ['A']\n")
        assert not self._reads("x = settings.read('toolset')\n")
        assert not self._reads("def f(environ=None):\n    return environ\n")


class TestTheResourceAddresses:
    """exegete:// is registered and listed; qualcoder:// (QualCoder's own
    server uses it too) is still answered, never listed, until v1.0."""

    def _resources(self):
        import asyncio
        listed = asyncio.run(server.mcp.list_resources())
        templates = asyncio.run(server.mcp.list_resource_templates())
        return ([str(r.uri) for r in listed],
                [t.uriTemplate for t in templates])

    def test_ten_under_the_new_scheme_none_under_the_old(self):
        concrete, templates = self._resources()
        assert len(concrete) + len(templates) == 10
        for address in concrete + templates:
            assert address.startswith(f"{names.RESOURCE_SCHEME}://")
            assert "qualcoder://" not in address

    def test_each_old_address_answers_as_its_twin(self, setup_server):
        import asyncio
        concrete, templates = self._resources()
        addresses = concrete + [t.replace("{code_id}", "1")
                                .replace("{file_id}", "1")
                                .replace("{case_id}", "1")
                                for t in templates]

        def read(uri):
            contents = asyncio.run(server.mcp.read_resource(uri))
            return [(c.content, c.mime_type) for c in contents]

        for address in addresses:
            old = "qualcoder://" + address.split("://", 1)[1]
            assert read(old) == read(address), address
            assert read("QUALCODER://" + address.split("://", 1)[1]) == \
                read(address)

    @pytest.mark.parametrize("address", ["qualcoder://nonexistent/x",
                                         "QUALCODER://nonexistent/x",
                                         "exegete://nonexistent/x"])
    def test_an_unknown_address_is_refused_under_its_own_name(
            self, address):
        """Fix round 1 (quality gate, note 5): an unknown old address was
        refused under its new twin's name."""
        import asyncio
        with pytest.raises(Exception) as caught:
            asyncio.run(server.mcp.read_resource(address))
        text = str(caught.value)
        assert address in text
        if not address.startswith("exegete"):
            assert "exegete://" not in text

    def test_the_served_texts_name_only_the_new_scheme(self):
        """Every address a served text gives is under the scheme names.py
        holds (a change there must reach the texts too)."""
        import re
        texts = [server.SERVER_INSTRUCTIONS, server.METHODS_GUIDANCE]
        texts += [t.description or "" for t in
                  server.mcp._tool_manager._tools.values()]
        schemes = set()
        for text in texts:
            schemes |= set(re.findall(r"\b([a-z]+)://", text))
        assert schemes <= {names.RESOURCE_SCHEME, "https", "http"}
        assert names.RESOURCE_SCHEME in schemes


class TestTheServersOwnProcessNames:

    @pytest.mark.parametrize("line", [
        "exegete",
        "/Users/x/.local/bin/exegete --stdio",
        "qualcoder-mcp",
        "/usr/bin/python3 -m exegete.server",
        "/usr/bin/python3 -m qualcoder_mcp.server",
        "uv run --frozen --directory /Users/x/Library/Application Support/"
        "Claude/Claude Extensions/local.mcpb.niccol-tempini.qualcoder-mcp "
        "exegete",
        "C:\\Users\\u\\venv\\Scripts\\exegete.exe",
    ])
    def test_this_server_is_never_taken_for_qualcoder(self, line):
        assert database._filter_qualcoder_processes([line]) == []

    def test_qualcoder_still_is(self):
        assert database._filter_qualcoder_processes(
            ["/Applications/QualCoder.app/Contents/MacOS/QualCoder"])

    def test_all_three_names_are_this_servers(self):
        assert set(database._OWN_NAMES) == {"exegete", "qualcoder-mcp",
                                            "qualcoder_mcp"}


class TestTheSandboxClearsBothSpellings:
    """conftest clears both spellings of all six settings before every
    test, so a developer's or CI's own value cannot leak in."""

    def test_no_setting_reaches_a_test(self):
        for spellings in SETTINGS.values():
            for name in spellings:
                assert name not in os.environ, name

    def test_even_when_the_run_starts_with_all_twelve_set(self, tmp_path):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("QUALCODER", "EXEGETE"))}
        values = {"toolset": "full", "ai_coder_name": "Developer",
                  "workspace": str(tmp_path / "developers-workspace"),
                  "workspace_required": "1", "allow_unknown_schema": "1",
                  "project_path": str(tmp_path / "Developers.qda")}
        for key, (new, old) in SETTINGS.items():
            env[new] = env[old] = values[key]
        home = tmp_path / "home"
        home.mkdir()
        env.update(HOME=str(home), USERPROFILE=str(home),
                   PYTHONDONTWRITEBYTECODE="1")
        node = (f"{Path(__file__).name}::TestTheSandboxClearsBothSpellings"
                f"::test_no_setting_reaches_a_test")
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "-p",
             "no:cacheprovider", node], cwd=str(Path(__file__).parent),
            capture_output=True, text=True, encoding="utf-8", env=env,
            timeout=240)
        assert proc.returncode == 0, proc.stdout[-3000:]
        assert "1 passed" in proc.stdout
