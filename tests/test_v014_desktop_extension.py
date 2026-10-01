# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14, the Claude Desktop extension (brief F): the package.

`scripts/build_desktop_extension.py` builds a `.mcpb` of the `uv` type
from a release: the app fetches uv, uv fetches Python and the
dependencies. These tests pin what the mandate asks of it:

- the manifest's version is pyproject.toml's, typed once: the template
  holds no version, and the build takes it from pyproject;
- its tool list is the server's own, asked of the server;
- the settings the app shows as a form (the tool set, the folder for
  projects, nothing secret) reach variables the server reads;
- the build is reproducible, and the package holds what uv needs;
- the manifest keeps to the MCPB manifest specification, version 0.4
  (mcpb 2.1.2's schema). CI also runs the official validator on it.
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import build_desktop_extension as build           # noqa: E402
import smoke_desktop_extension as smoke           # noqa: E402
import exegete.server as server             # noqa: E402
from exegete import database                # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib

TEMPLATE = json.loads((REPO / build.TEMPLATE).read_text(encoding="utf-8"))
with open(REPO / "pyproject.toml", "rb") as _handle:
    PYPROJECT = tomllib.load(_handle)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """One build from the files on disk: (manifest, files, mcpb path)."""
    manifest, files = build.bundle(build.TreeSource(REPO))
    target = tmp_path_factory.mktemp("mcpb") / "package.mcpb"
    build.write_mcpb(files, target, build.EARLIEST_ZIP_TIME)
    return manifest, files, target


def _server_tools(mode):
    server._apply_toolset(mode)
    return [t.name for t in asyncio.run(server.mcp.list_tools())]


# ---------------------------------------------------------------------------
# Typed once
# ---------------------------------------------------------------------------

class TestTypedOnce:

    def test_the_template_holds_no_field_the_build_fills(self):
        assert set(build.GENERATED) & set(TEMPLATE) == set()
        text = (REPO / build.TEMPLATE).read_text(encoding="utf-8")
        assert PYPROJECT["project"]["version"] not in text

    def test_the_version_is_pyprojects(self, built):
        manifest, files, _ = built
        assert manifest["version"] == PYPROJECT["project"]["version"]
        assert json.loads(files["manifest.json"])["version"] == \
            PYPROJECT["project"]["version"]

    def test_the_rest_of_pyprojects_fields(self, built):
        manifest, _, _ = built
        meta = PYPROJECT["project"]
        # v0.14.1, the rename: the identifier is NOT pyproject's name any
        # more, which became `exegete`; it stays `qualcoder-mcp` for good
        # (tests/test_v0141_rename.py pins it against a renamed copy).
        assert manifest["name"] == build.EXTENSION_NAME == "qualcoder-mcp"
        assert manifest["name"] != meta["name"]
        assert manifest["license"] == meta["license"]
        assert manifest["keywords"] == meta["keywords"]
        assert manifest["author"]["name"] == meta["authors"][0]["name"]
        assert "email" not in manifest["author"]      # not a support channel
        assert manifest["support"] == meta["urls"]["Issues"]
        assert manifest["compatibility"]["runtimes"]["python"] == \
            meta["requires-python"]

    @pytest.mark.parametrize("version", ["0.14.0a1", "0.14", "v0.14.0",
                                         "0.14.0-alpha.01"])
    def test_a_version_that_is_not_semver_is_refused(self, version):
        project = {"project": dict(PYPROJECT["project"], version=version)}
        with pytest.raises(build.BuildError, match="semantic version"):
            build.build_manifest(TEMPLATE, project, [])

    @pytest.mark.parametrize("version", ["0.13.0-alpha", "0.14.0",
                                         "1.0.0-rc.1+build.5"])
    def test_a_semver_version_is_kept_as_written(self, version):
        project = {"project": dict(PYPROJECT["project"], version=version)}
        assert build.build_manifest(TEMPLATE, project, [])["version"] == \
            version

    def test_a_typed_field_is_refused(self):
        with pytest.raises(build.BuildError, match="version"):
            build.build_manifest(dict(TEMPLATE, version="9.9.9"),
                                 PYPROJECT, [])

    def test_an_unplaced_field_is_refused(self):
        # v0.14.1: `icon` is placed now (tests/test_v0141_rename.py)
        with pytest.raises(build.BuildError, match="screenshots"):
            build.build_manifest(dict(TEMPLATE, screenshots=["a.png"]),
                                 PYPROJECT, [])


class TestTheToolsAreTheServers:

    def test_the_list_is_the_lifecycle_set_in_the_servers_order(self, built):
        manifest, _, _ = built
        names = [t["name"] for t in manifest["tools"]]
        assert names == _server_tools("lifecycle")
        assert "create_project" in names

    def test_every_other_set_is_inside_it(self, built):
        manifest, _, _ = built
        names = {t["name"] for t in manifest["tools"]}
        for mode in ("full", "core"):       # `full` first: `core` removes
            assert set(_server_tools(mode)) <= names, mode
        assert manifest["tools_generated"] is False

    def test_each_summary_is_one_line_from_the_description(self, built):
        manifest, _, _ = built
        descriptions = {t.name: t.description for t in
                        asyncio.run(server.mcp.list_tools())}
        for tool in manifest["tools"]:
            text = tool["description"]
            assert text and "\n" not in text
            assert len(text) <= build.SUMMARY_LIMIT
            if tool["name"] in descriptions:
                flat = " ".join(descriptions[tool["name"]].split())
                assert flat.startswith(text.rstrip(".").rstrip())

    def test_the_summary_rule(self):
        assert build.summary("One. Two.") == "One."
        assert build.summary("First line\n  goes on. Next") == \
            "First line goes on."
        assert build.summary("Para one.\n\nPara two.") == "Para one."
        assert build.summary("e.g. lower case goes on. Then") == \
            "e.g. lower case goes on."
        long = "word " * 100
        cut = build.summary(long)
        assert len(cut) <= build.SUMMARY_LIMIT and cut.endswith("...")

    def test_prompts_are_left_to_the_server(self, built):
        """The specification's prompts carry a fixed text; the server's
        four are built at call time, so none is listed and the manifest
        says the server makes them."""
        manifest, _, _ = built
        assert "prompts" not in manifest
        assert manifest["prompts_generated"] is True
        assert len(asyncio.run(server.mcp.list_prompts())) > 0


# ---------------------------------------------------------------------------
# The settings form
# ---------------------------------------------------------------------------

class TestTheSettings:

    def test_two_settings_and_nothing_secret(self):
        config = TEMPLATE["user_config"]
        assert set(config) == {"toolset", "projects_folder"}
        assert not any(option.get("sensitive") for option in config.values())
        assert not any(option.get("required") for option in config.values())

    def test_the_tool_set_defaults_to_lifecycle_and_names_the_others(self):
        option = TEMPLATE["user_config"]["toolset"]
        assert option["type"] == "string"
        assert option["default"] == "lifecycle"
        for mode in server._VALID_TOOLSET_MODES:
            assert f"{mode}:" in option["description"]

    def test_an_empty_folder_stops_the_extension(self, monkeypatch):
        """Fix round 1: the app lays a saved empty value over the default,
        and blank used to mean ~/Documents. The manifest's marker makes a
        blank folder stop the server, and the setting says so."""
        option = TEMPLATE["user_config"]["projects_folder"]
        assert "Leaving it empty stops the extension from starting" in \
            option["description"]
        for name, value in TEMPLATE["server"]["mcp_config"]["env"].items():
            if "${" not in value:
                monkeypatch.setenv(name, value)
        monkeypatch.setenv(database.WORKSPACE_ENV, "")
        problem = server._workspace_start_problem()
        assert problem.startswith(f"{database.WORKSPACE_ENV} is empty")

    def test_the_folder_is_a_picker_outside_documents(self):
        option = TEMPLATE["user_config"]["projects_folder"]
        assert option["type"] == "directory"
        assert "multiple" not in option
        default = option["default"]
        # `~`, which the server expands: the app does not expand a
        # ${HOME} inside a setting's default (one-pass substitution)
        assert default.startswith("~/") and "${" not in default
        assert "Documents" not in default and "Desktop" not in default

    def test_each_setting_reaches_a_variable_the_server_reads(self):
        """v0.14.1: each of the three under both spellings, always the
        same value, until v1.0 (tests/test_v0141_compat.py says why)."""
        from exegete import names
        env = TEMPLATE["server"]["mcp_config"]["env"]
        expected = {}
        for key, value in (("toolset", "${user_config.toolset}"),
                           ("workspace", "${user_config.projects_folder}"),
                           ("workspace_required", "1")):
            for name in names.SETTINGS[key]:
                expected[name] = value
        assert env == expected
        source = (REPO / "src" / "exegete" / "server.py").read_text(
            encoding="utf-8")
        assert 'env_settings.read("toolset")' in source
        assert database.WORKSPACE_ENV == "EXEGETE_WORKSPACE"
        assert database.WORKSPACE_REQUIRED_ENV == "EXEGETE_WORKSPACE_REQUIRED"

    def test_the_default_folder_is_accepted_by_the_server(self, monkeypatch):
        monkeypatch.setenv(database.WORKSPACE_ENV,
                           TEMPLATE["user_config"]["projects_folder"]
                           ["default"])
        assert server._workspace_start_problem() is None
        assert database.default_workspace().parent == \
            database.standard_workspace().parent.parent      # the home

    def test_uv_starts_the_command_pyproject_installs(self):
        server_block = TEMPLATE["server"]
        assert server_block["type"] == "uv"
        config = server_block["mcp_config"]
        assert config["command"] == "uv"
        scripts = PYPROJECT["project"]["scripts"]
        # --frozen (fix round 1): each start installs exactly the lock,
        # never re-resolving it against a tester's own uv settings.
        # --extra pdf-epub (0.14.3, provisional, decision 1): the
        # optional part for PDF and EPUB import, switched on here
        assert config["args"] == ["run", "--frozen", "--extra",
                                  *EXTENSION_EXTRAS, "--directory",
                                  "${__dirname}", *scripts]
        assert set(EXTENSION_EXTRAS) <= set(
            PYPROJECT["project"]["optional-dependencies"])
        assert scripts == {"exegete": "exegete.server:main"}
        assert (REPO / server_block["entry_point"]).is_file()


class TestTheSmokeScriptDoesWhatTheAppDoes:
    """scripts/smoke_desktop_extension.py stands in for Claude Desktop in
    CI and the trials, so its substitution and environment are the
    app's (fix round 1), read from Claude Desktop 2.9939.2's code."""

    MANIFEST = {
        "name": "qualcoder-mcp", "author": {"name": "Niccolò Tempini"},
        "server": {"mcp_config": {
            "command": "uv",
            "args": ["run", "--directory", "${__dirname}", "x"],
            "env": {"A": "${user_config.folder}",
                    "B": "${user_config.flag}",
                    "C": "${HOME}/plain"}}},
        "user_config": {
            "folder": {"default": "${HOME}/Projects"},
            "flag": {"default": False}},
    }

    def test_a_home_inside_a_default_is_left_as_it_is(self, tmp_path):
        config = smoke.launch_config(self.MANIFEST, tmp_path, {})
        assert config["env"]["A"] == "${HOME}/Projects"
        assert config["env"]["C"] == str(Path.home()) + "/plain"
        assert config["env"]["B"] == "false"
        assert config["args"][2] == str(tmp_path)

    def test_a_saved_value_is_laid_over_the_default(self, tmp_path):
        config = smoke.launch_config(self.MANIFEST, tmp_path,
                                     {"folder": "/chosen", "flag": True})
        assert config["env"]["A"] == "/chosen"
        assert config["env"]["B"] == "true"

    def test_the_server_gets_the_apps_short_list_only(self):
        environ = {"HOME": "/h", "PATH": "/p", "USERPROFILE": "C:\\h",
                   "APPDATA": "C:\\a", "SECRET_TOKEN": "x",
                   "UV_INDEX_URL": "https://mirror", "SHELL": "() { :; }"}
        env = smoke.server_environment({"env": {"A": "1"}}, environ,
                                       extra={"UV_OFFLINE": "1"})
        assert "SECRET_TOKEN" not in env and "UV_INDEX_URL" not in env
        assert "SHELL" not in env            # a shell function is left out
        assert env["A"] == "1" and env["UV_OFFLINE"] == "1"
        assert env["PATH"] == "/p"
        expected = ({"HOME"} if os.name != "nt" else
                    {"USERPROFILE", "APPDATA"})
        assert expected <= set(env)

    def test_the_folder_name_is_the_apps(self):
        assert smoke.extension_id(self.MANIFEST) == \
            "local.mcpb.niccol-tempini.qualcoder-mcp"


# ---------------------------------------------------------------------------
# The package
# ---------------------------------------------------------------------------

class TestThePackage:

    def test_it_holds_what_uv_needs_and_no_more(self, built):
        _, files, target = built
        meta = PYPROJECT["project"]
        package = sorted(
            p.relative_to(REPO).as_posix()
            for p in (REPO / build.PACKAGE).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
            and p.suffix != ".pyc")
        # v0.14.1: and the icon the manifest names (test_v0141_mark.py)
        expected = {"manifest.json", ".python-version", "pyproject.toml",
                    "uv.lock", meta["readme"], *meta["license-files"],
                    *package, "icon.png"}
        assert set(files) == expected
        with zipfile.ZipFile(target) as z:
            assert sorted(z.namelist()) == sorted(expected)
            for name in expected - {"manifest.json", ".python-version",
                                    "icon.png"}:
                assert z.read(name) == (REPO / name).read_bytes(), name
            assert z.read("icon.png") == (
                REPO / build.ICON_FOLDER / "icon.png").read_bytes()

    def test_it_asks_uv_for_a_python_ci_tests(self, built):
        _, files, _ = built
        assert files[".python-version"] == b"3.13\n"
        ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8")
        matrix = re.search(r"python-version: \[(.*?)\]", ci).group(1)
        assert f'"{build.PYTHON_VERSION}"' in matrix

    def test_each_entry_is_fixed(self, built):
        _, _, target = built
        with zipfile.ZipFile(target) as z:
            infos = z.infolist()
        assert [i.filename for i in infos] == sorted(i.filename
                                                     for i in infos)
        for info in infos:
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert info.external_attr == 0o100644 << 16
            assert info.date_time == (1980, 1, 1, 0, 0, 0)

    def test_the_same_files_give_the_same_bytes(self, built, tmp_path):
        _, files, target = built
        again = tmp_path / "again.mcpb"
        build.write_mcpb(dict(reversed(list(files.items()))), again,
                         build.EARLIEST_ZIP_TIME)
        assert again.read_bytes() == target.read_bytes()
        later = tmp_path / "later.mcpb"
        build.write_mcpb(files, later, 1790000000)
        assert later.read_bytes() != target.read_bytes()   # the date counts


class TestTheLockShippedWithIt:
    """uv.lock travels in the package, and `uv sync` installs what it
    records, so it must describe this pyproject.toml."""

    def _lock(self):
        with open(REPO / "uv.lock", "rb") as handle:
            return tomllib.load(handle)

    def _ours(self):
        return next(p for p in self._lock()["package"]
                    if p["name"] == PYPROJECT["project"]["name"])

    def test_it_records_this_version(self):
        from packaging.version import Version
        assert self._ours()["version"] == \
            str(Version(PYPROJECT["project"]["version"]))

    def test_it_records_these_requirements(self):
        lock = self._lock()
        assert lock["requires-python"] == \
            PYPROJECT["project"]["requires-python"]
        recorded = {r["name"]: r.get("specifier", "") for r in
                    self._ours()["metadata"]["requires-dist"]
                    if "marker" not in r}
        declared = {}
        for requirement in PYPROJECT["project"]["dependencies"]:
            name, spec = re.match(r"([A-Za-z0-9_.-]+)(.*)",
                                  requirement).groups()
            declared[name] = spec.replace(" ", "")
        assert recorded == declared


# ---------------------------------------------------------------------------
# A wheel for every computer (fix round 1: cryptography 50.0.1 had none
# for Intel Macs or Windows on Arm, so the app's `uv sync` compiled it
# and failed). The extension's Python is the .python-version's.
# ---------------------------------------------------------------------------

ENVIRONMENTS = {
    ("darwin", "arm64"): ("macosx_", ("_arm64", "_universal2")),
    ("darwin", "x86_64"): ("macosx_", ("_x86_64", "_universal2")),
    ("win32", "AMD64"): ("win_amd64", ("",)),
    ("win32", "ARM64"): ("win_arm64", ("",)),
    ("linux", "x86_64"): ("manylinux", ("_x86_64",)),
    ("linux", "aarch64"): ("manylinux", ("_aarch64",)),
}


def _marker_environment(system, machine, python=build.PYTHON_VERSION):
    return {
        "sys_platform": system, "platform_machine": machine,
        "python_version": python, "python_full_version": f"{python}.0",
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
        "os_name": "nt" if system == "win32" else "posix",
        "platform_system": {"darwin": "Darwin", "win32": "Windows",
                            "linux": "Linux"}[system],
        "platform_release": "", "platform_version": "", "extra": "",
    }


# The optional parts the extension's manifest switches on (0.14.3).
EXTENSION_EXTRAS = ("pdf-epub",)


def _wheel_fits(filename, system, machine, python=build.PYTHON_VERSION):
    """Whether a wheel's tags suit CPython `python` on that computer."""
    stem = filename[:-len(".whl")]
    pythons, abi, platforms = stem.split("-")[-3:]
    minor = int(python.split(".")[1])

    def python_fits(tag):
        if tag in ("py3", f"py3{minor}", "py2.py3"):
            return True
        if tag.startswith("cp3") and tag[3:].isdigit():
            return int(tag[3:]) == minor or (
                abi == "abi3" and int(tag[3:]) <= minor)
        return False

    if not any(python_fits(t) for t in pythons.split(".")):
        return False
    if abi not in ("none", "abi3", f"cp3{minor}"):
        return False
    start, ends = ENVIRONMENTS[(system, machine)]
    return any(p == "any" or (p.startswith(start) and
                              any(p.endswith(e) for e in ends))
               for p in platforms.split("."))


def lock_wheel_gaps(lock, root, system, machine, root_extras=()):
    """(package, version) the lock would install for `root` (with
    `root_extras`) on that computer with no wheel that fits it."""
    from packaging.markers import Marker
    environment = _marker_environment(system, machine)
    entries = {}
    for package in lock["package"]:
        entries.setdefault(package["name"], []).append(package)

    def entry(dependency):
        found = entries[dependency["name"]]
        if "version" in dependency:
            found = [p for p in found
                     if p["version"] == dependency["version"]]
        assert len(found) == 1, dependency
        return found[0]

    gaps, seen = [], set()
    todo = [(entries[root][0], tuple(sorted(root_extras)))]
    while todo:
        package, extras = todo.pop()
        key = (package["name"], package["version"], extras)
        if key in seen:
            continue
        seen.add(key)
        wanted = list(package.get("dependencies", []))
        for extra in extras:
            wanted += package.get("optional-dependencies", {}).get(extra, [])
        for dependency in wanted:
            marker = dependency.get("marker")
            if marker and not Marker(marker).evaluate(environment):
                continue
            todo.append((entry(dependency),
                         tuple(sorted(dependency.get("extra", [])))))
        if package["name"] == root:
            continue
        wheels = [w["url"].rsplit("/", 1)[1]
                  for w in package.get("wheels", [])]
        if not any(_wheel_fits(w, system, machine) for w in wheels):
            gaps.append((package["name"], package["version"]))
    return sorted(set(gaps))


class TestAWheelForEveryComputer:

    def _lock(self):
        with open(REPO / "uv.lock", "rb") as handle:
            return tomllib.load(handle)

    def test_uv_is_told_the_computers_and_never_to_compile(self):
        settings = PYPROJECT["tool"]["uv"]
        from packaging.markers import Marker
        told = set()
        for text in settings["required-environments"]:
            for system, machine in ENVIRONMENTS:
                if Marker(text).evaluate(
                        _marker_environment(system, machine)):
                    told.add((system, machine))
        assert told == set(ENVIRONMENTS)
        assert "cryptography" in settings["no-build-package"]
        assert self._lock()["required-markers"]

    def test_the_build_backend_is_pinned_for_uv(self):
        """Build requirements are not in uv.lock, so without a pin the
        extension's install builds the package with whatever setuptools
        is newest that day (fix round 1). Pinned exactly, within
        [build-system]'s own floor, and recorded in the lock."""
        from packaging.requirements import Requirement
        from packaging.version import Version
        pins = PYPROJECT["tool"]["uv"]["build-constraint-dependencies"]
        assert len(pins) == 1
        pin = Requirement(pins[0])
        assert pin.name == "setuptools"
        (spec,) = pin.specifier
        assert spec.operator == "=="
        floor = Requirement(PYPROJECT["build-system"]["requires"][0])
        assert floor.name == "setuptools"
        assert Version(spec.version) in floor.specifier
        assert self._lock()["manifest"]["build-constraints"] == [
            {"name": "setuptools", "specifier": f"=={spec.version}"}]

    @pytest.mark.parametrize("system,machine", sorted(ENVIRONMENTS))
    def test_every_package_installed_has_a_wheel(self, system, machine):
        # The extension installs the package with its optional part
        # (0.14.3), so the walk starts from the root with that extra
        assert lock_wheel_gaps(self._lock(), PYPROJECT["project"]["name"],
                               system, machine,
                               root_extras=EXTENSION_EXTRAS) == []

    def test_the_walk_follows_the_roots_extra(self):
        """Without the extra, PyMuPDF is not walked; with it, it is."""
        lock = self._lock()
        name = PYPROJECT["project"]["name"]
        root = next(p for p in lock["package"] if p["name"] == name)
        assert "pymupdf" in [d["name"] for d in
                             root["optional-dependencies"]["pdf-epub"]]
        assert "pymupdf" not in [d["name"] for d in
                                 root.get("dependencies", [])]

    def test_the_versions_each_computer_gets(self):
        from packaging.markers import Marker
        lock = self._lock()
        crypto = {}
        for system, machine in ENVIRONMENTS:
            pyjwt = next(p for p in lock["package"] if p["name"] == "pyjwt")
            for dependency in pyjwt["optional-dependencies"]["crypto"]:
                if Marker(dependency["marker"]).evaluate(
                        _marker_environment(system, machine)):
                    crypto[(system, machine)] = dependency["version"]
        assert crypto[("darwin", "x86_64")] == "48.0.1"
        assert crypto[("win32", "ARM64")] == "46.0.3"

    def test_the_check_finds_a_missing_wheel(self):
        """The failure the gate found, in miniature: a package with only
        an Apple-chip Mac wheel and a Windows x64 wheel."""
        lock = {"package": [
            {"name": "root", "version": "1", "dependencies": [
                {"name": "native"}]},
            {"name": "native", "version": "2", "wheels": [
                {"url": "https://x/native-2-cp311-abi3-macosx_11_0_arm64.whl"},
                {"url": "https://x/native-2-cp311-abi3-win_amd64.whl"}]},
        ]}
        assert lock_wheel_gaps(lock, "root", "darwin", "arm64") == []
        assert lock_wheel_gaps(lock, "root", "win32", "AMD64") == []
        assert lock_wheel_gaps(lock, "root", "darwin", "x86_64") == [
            ("native", "2")]
        assert lock_wheel_gaps(lock, "root", "win32", "ARM64") == [
            ("native", "2")]

    def test_the_tag_rule(self):
        fits = _wheel_fits
        assert fits("a-1-py3-none-any.whl", "win32", "ARM64")
        assert fits("a-1-cp313-cp313-win_arm64.whl", "win32", "ARM64")
        assert not fits("a-1-cp312-cp312-win_arm64.whl", "win32", "ARM64")
        assert fits("a-1-cp311-abi3-macosx_10_9_universal2.whl",
                    "darwin", "x86_64")
        assert not fits("a-1-cp314-abi3-macosx_11_0_arm64.whl",
                        "darwin", "arm64")
        assert fits("a-1-cp313-cp313-manylinux_2_17_x86_64."
                    "manylinux2014_x86_64.whl", "linux", "x86_64")
        assert not fits("a-1-cp313-cp313-musllinux_1_2_x86_64.whl",
                        "linux", "x86_64")


class TestReadingARelease:

    def test_a_commit_is_read_from_git_not_the_disk(self):
        try:
            source = build.GitSource("HEAD")
        except build.BuildError:
            pytest.skip("not a git checkout")
        assert re.fullmatch(r"[0-9a-f]{40}", source.commit)
        assert source.epoch > build.EARLIEST_ZIP_TIME
        tracked = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", "--",
             build.PACKAGE], cwd=str(REPO), capture_output=True,
            text=True, check=True).stdout.split()
        assert source.files_under(build.PACKAGE) == sorted(tracked)
        assert source.read("pyproject.toml") == subprocess.run(
            ["git", "show", "HEAD:pyproject.toml"], cwd=str(REPO),
            capture_output=True, check=True).stdout

    def test_an_unknown_ref_is_refused_in_words(self):
        try:
            build.GitSource("HEAD")
        except build.BuildError:
            pytest.skip("not a git checkout")
        with pytest.raises(build.BuildError, match="git rev-parse"):
            build.GitSource("no-such-ref-anywhere")


# ---------------------------------------------------------------------------
# The specification: MCPB manifest 0.4, as mcpb 2.1.2's schema has it
# (src/schemas/0.4.ts, strict objects). CI runs the official validator;
# this copy of its key sets runs in every job, without Node.
# ---------------------------------------------------------------------------

SPEC_TOP = {"$schema", "dxt_version", "manifest_version", "name",
            "display_name", "version", "description", "long_description",
            "author", "repository", "homepage", "documentation", "support",
            "icon", "icons", "screenshots", "localization", "server", "tools",
            "tools_generated", "prompts", "prompts_generated", "keywords",
            "license", "privacy_policies", "compatibility", "user_config",
            "_meta"}
SPEC_OPTION = {"type", "title", "description", "required", "default",
               "multiple", "sensitive", "min", "max"}


class TestTheSpecification:

    def test_every_key_is_one_the_schema_knows(self, built):
        manifest, _, _ = built
        assert manifest["manifest_version"] == "0.4"
        assert set(manifest) <= SPEC_TOP
        assert {"name", "version", "description", "author",
                "server"} <= set(manifest)
        assert set(manifest["author"]) <= {"name", "email", "url"}
        assert set(manifest["repository"]) == {"type", "url"}
        assert set(manifest["server"]) == {"type", "entry_point",
                                           "mcp_config"}
        assert set(manifest["server"]["mcp_config"]) <= {
            "command", "args", "env", "platform_overrides"}
        assert set(manifest["compatibility"]) <= {
            "claude_desktop", "platforms", "runtimes"}
        assert set(manifest["compatibility"]["platforms"]) <= {
            "darwin", "win32", "linux"}
        assert set(manifest["compatibility"]["runtimes"]) <= {
            "python", "node"}
        for tool in manifest["tools"]:
            assert set(tool) <= {"name", "description"}
        for option in manifest["user_config"].values():
            assert set(option) <= SPEC_OPTION
            assert {"type", "title", "description"} <= set(option)
            assert option["type"] in {"string", "number", "boolean",
                                      "directory", "file"}
        for url in (manifest["homepage"], manifest["documentation"],
                    manifest["support"], manifest["repository"]["url"],
                    manifest["author"]["url"]):
            assert url.startswith("https://")

    def test_the_official_validator_is_pinned(self):
        folder = REPO / "packaging" / "desktop-extension" / "validator"
        declared = json.loads((folder / "package.json").read_text(
            encoding="utf-8"))
        assert declared["devDependencies"] == {"@anthropic-ai/mcpb": "2.1.2"}
        lock = json.loads((folder / "package-lock.json").read_text(
            encoding="utf-8"))
        entry = lock["packages"]["node_modules/@anthropic-ai/mcpb"]
        assert entry["version"] == "2.1.2"
        assert entry["integrity"].startswith("sha512-")
        assert all(p.get("integrity") for name, p in lock["packages"].items()
                   if name)


# ---------------------------------------------------------------------------
# CI builds it on every run
# ---------------------------------------------------------------------------

class TestCiBuildsIt:

    @staticmethod
    def _job(name):
        from test_v012_workflow_pins import WORKFLOWS, _jobs
        jobs = {job["name"]: "\n".join(job["lines"])
                for job in _jobs(WORKFLOWS / "ci.yml")}
        return jobs[name]

    def test_on_every_platform_from_the_commit_twice(self):
        job = self._job("desktop-extension")
        assert "os: [ubuntu-latest, windows-latest, macos-latest]" in job
        runs = re.findall(r"python scripts/build_desktop_extension\.py "
                          r"--ref HEAD --out (\S+)", job)
        assert runs == ["dist/mcpb", "dist/again"]
        assert "cmp dist/mcpb/*.mcpb dist/again/*.mcpb" in job

    def test_uploaded_before_any_third_party_tool_runs(self):
        job = self._job("desktop-extension")
        upload = job.index("actions/upload-artifact@")
        validate = job.index("npm ci --ignore-scripts")
        uv = job.index("pip install uv==0.9.7")
        wheels = job.index("uv sync --frozen --dry-run")
        smoke = job.index("python scripts/smoke_desktop_extension.py")
        assert upload < validate < uv < wheels < smoke

    def test_the_lock_is_asked_for_every_computer(self):
        job = self._job("desktop-extension")
        loop = re.search(r"for target in ([^;]+); do", job).group(1).split()
        assert set(loop) == {
            "aarch64-apple-darwin", "x86_64-apple-darwin",
            "x86_64-pc-windows-msvc", "aarch64-pc-windows-msvc",
            "x86_64-unknown-linux-gnu", "aarch64-unknown-linux-gnu"}
        assert len(loop) == len(ENVIRONMENTS)
        # with the optional part the manifest switches on (0.14.3)
        assert ('uv sync --frozen --dry-run --no-install-project --no-build '
                '--extra pdf-epub --python "$(cat .python-version)" '
                '--python-platform "$target"') in job

    def test_the_official_validator_checks_the_manifest(self):
        job = self._job("desktop-extension")
        assert "working-directory: packaging/desktop-extension/validator" \
            in job
        assert "npx --no-install mcpb validate " \
               "../../../dist/mcpb/exegete-*/manifest.json" in job

    def test_it_is_installed_and_started_as_the_app_does(self):
        job = self._job("desktop-extension")
        line = next(l for l in job.splitlines()
                    if "python scripts/smoke_desktop_extension.py" in l
                    and not l.strip().startswith("#"))
        for part in ("--expect-tools manifest", "--create",
                     "--offline-restart", 'HOME="$home"',
                     'USERPROFILE="$home"'):
            assert part in line

    def test_the_platforms_give_the_same_bytes(self):
        job = self._job("desktop-extension-same")
        assert "needs: desktop-extension" in job
        assert "pattern: desktop-extension-*" in job
        assert "sort -u | wc -l)\" -eq 1" in job
        # and exactly three arrived: two alike would pass the line above
        assert 'test "$(ls builds/*/*.mcpb | wc -l)" -eq 3' in job
        platforms = re.search(r"os: \[([^\]]+)\]",
                              self._job("desktop-extension")).group(1)
        assert len(platforms.split(",")) == 3


# ---------------------------------------------------------------------------
# The documents
# ---------------------------------------------------------------------------

def _flat(name):
    text = (REPO / name).read_text(encoding="utf-8")
    return " ".join(text.replace("\n>", " ").split())


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:end if end != -1 else len(text)]


class TestTheDocuments:

    def test_install_starts_with_the_extension(self):
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", text, flags=re.M)
        assert headings[0] == "Claude Desktop: the one-click extension " \
                              "(recommended)"
        section = " ".join(_section(
            text, "## Claude Desktop: the one-click extension").split())
        option = TEMPLATE["user_config"]
        assert f"`{option['toolset']['default']}` (the default)" in section
        for mode in server._VALID_TOOLSET_MODES:
            assert f"`{mode}`" in section
        assert f"`{option['projects_folder']['default']}`" in section
        assert "double-click the file" in section
        assert "This extension isn't signed" in section
        assert "the Terminal route" in section

    def test_install_documents_every_variable_the_server_reads(self):
        # v0.14.1: every setting is read through one table, under both
        # spellings (names.SETTINGS)
        from exegete import names
        read = {new for new, old in names.SETTINGS.values()}
        text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
        section = _section(text, "## Environment variables the server reads")
        documented = set(re.findall(r"^- `(EXEGETE_[A-Z_]+)`", section,
                                    flags=re.M))
        assert documented == read
        # and every earlier spelling the server still reads, named there
        for new, old in names.SETTINGS.values():
            assert f"`{old}`" in section, old

    def test_readmes_install_line_points_to_it(self):
        """v0.14.1: README's "Start here" gives the one-click route before
        the Terminal route, and links INSTALL.md's section for it."""
        text = (REPO / "README.md").read_text(encoding="utf-8")
        start = _section(text, "## Start here")
        one_click = _section(start, "### Claude Desktop, with one click")
        one_click = one_click[:one_click.index("**A first project.**")]
        assert start.index("### Claude Desktop, with one click") \
            < start.index("**Other assistants.**")
        assert ("INSTALL.md#claude-desktop-the-one-click-extension-"
                "recommended") in one_click
        assert "double-click the file" in " ".join(one_click.split()).lower()

    def test_the_workspace_setting_is_named_where_the_folder_is(self):
        # v0.14.1: README names only the extension's folder, which
        # needs no qualifier; the workspace paragraphs moved to TOOLS.md
        for name in ("TOOLS.md", "PRIVACY.md", "INSTALL.md"):
            assert "EXEGETE_WORKSPACE" in _flat(name), name
        assert "Qualcoder MCP Projects" not in _flat("README.md")
        assert "QUALCODER_MCP_WORKSPACE" in _flat("CHANGELOG.md").split(
            "## [0.13")[0]


class TestEverySectionNamingTheOldFolderNamesTheSetting:
    """Fix round 1 (QA, major): README and the workflow guide sent
    researchers to `~/Documents/Qualcoder MCP Projects` on the extension
    route, where the workspace is `~/QualCoder projects`. Checked per
    section, not per file: README named the setting elsewhere, which a
    per-file check would have taken as enough."""

    QUALIFIERS = ("EXEGETE_WORKSPACE", "QUALCODER_MCP_WORKSPACE",
                  "QualCoder projects", "unless the host")

    @staticmethod
    def _sections(text):
        return re.split(r"(?m)^#{2,4} ", text)

    def _offenders(self, name, text):
        found = []
        for section in self._sections(text):
            flat = " ".join(section.split())
            # v0.14.1: the Terminal workspace's new name too
            if any(folder in flat for folder in (
                    "Qualcoder MCP Projects", "Documents/Exegete projects")) \
                    and not any(q in flat for q in self.QUALIFIERS):
                found.append(f"{name}: {flat[:60]}")
        return found

    def test_every_shipped_document(self):
        documents = sorted(p for p in REPO.glob("*.md")
                           if p.name != "CHANGELOG.md")
        assert {"README.md", "TOOLS.md", "AI_CODING_WORKFLOW.md",
                "INSTALL.md", "PRIVACY.md"} <= {p.name for p in documents}
        offenders = []
        for path in documents:
            offenders += self._offenders(
                path.name, path.read_text(encoding="utf-8"))
        assert offenders == []

    def test_the_check_would_notice(self):
        text = ("## Workspace\n\nThe workspace is `~/Documents/Qualcoder "
                "MCP\nProjects/`.\n\n## Other\n\nSet "
                "QUALCODER_MCP_WORKSPACE.\n")
        assert len(self._offenders("x", text)) == 1
        assert len(self._offenders("x", text.replace(
            "Qualcoder MCP\nProjects", "Exegete\nprojects"))) == 1
