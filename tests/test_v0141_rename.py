# SPDX-License-Identifier: LGPL-3.0-or-later
"""v0.14.1, the rename to Exegete: what must never change, and the move.

qualcoder-mcp became Exegete in 0.14.1-alpha. The package, the command
and the PyPI name are now `exegete`; some names stay for good, because
something outside this repository holds them:

- the extension's identifier `qualcoder-mcp` with the author's name
  exactly "Niccolò Tempini": together they are the folder Claude Desktop
  installs into and keeps the settings under, so a change would give
  every tester a second extension instead of an update (the owner's
  ruling of 26 September 2026);
- `exegete.server:main`, the entry point the old name's last release
  will call for good (it asks for `exegete>=` some version, with no
  upper limit): never removed, never renamed.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import build_desktop_extension as build           # noqa: E402
import smoke_desktop_extension as smoke           # noqa: E402
import exegete                                    # noqa: E402
from exegete import names                         # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10, where pytest itself needs tomli
    import tomli as tomllib


def _pyproject():
    with open(REPO / "pyproject.toml", "rb") as handle:
        return tomllib.load(handle)


def test_the_package_is_the_one_in_this_tree():
    """A leftover editable install of the old name must never answer for
    this tree (the developer's trap on the rename)."""
    assert Path(exegete.__file__).resolve().is_relative_to(REPO / "src")


class TestTheNewNames:

    def test_pyproject_names_the_distribution(self):
        assert _pyproject()["project"]["name"] == names.DISTRIBUTION \
            == "exegete"

    def test_the_version_is_read_under_the_new_name(self):
        text = (REPO / "src" / "exegete" / "__init__.py").read_text(
            encoding="utf-8")
        assert "__version__ = version(DISTRIBUTION)" in text
        assert "from .names import DISTRIBUTION" in text

    def test_the_lock_records_the_project_under_its_new_name(self):
        with open(REPO / "uv.lock", "rb") as handle:
            lock = tomllib.load(handle)
        editable = [p["name"] for p in lock["package"]
                    if p.get("source") == {"editable": "."}]
        assert editable == [names.DISTRIBUTION]
        assert "qualcoder-mcp" not in {p["name"] for p in lock["package"]}


class TestTheEntryPointIsAPromise:
    """`exegete.server:main` is never removed: the old name's last
    release calls it for good."""

    def test_pyproject_maps_the_command_to_it(self):
        assert _pyproject()["project"]["scripts"] == {
            "exegete": "exegete.server:main"}

    def test_it_exists_and_is_callable(self):
        import exegete.server
        assert callable(exegete.server.main)


class TestTheExtensionKeepsItsIdentity:

    def test_the_identifier_is_fixed(self):
        assert build.EXTENSION_NAME == "qualcoder-mcp"

    def test_the_author_is_spelt_exactly_so(self):
        assert _pyproject()["project"]["authors"][0]["name"] == \
            "Niccolò Tempini"

    def test_the_app_computes_the_same_folder(self):
        manifest = build.build_manifest(
            json.loads((REPO / build.TEMPLATE).read_text(encoding="utf-8")),
            _pyproject(), [])
        assert smoke.extension_id(manifest) == \
            "local.mcpb.niccol-tempini.qualcoder-mcp"

    def test_a_renamed_copy_keeps_the_identifier(self, tmp_path,
                                                  monkeypatch):
        """Rename the package in a copy of the tree and build it: the
        identifier does not follow pyproject's name; the file's name
        does follow the stem."""
        copy = tmp_path / "tree"
        for name in ("pyproject.toml", "uv.lock", "README.md", "NOTICE",
                     "COPYING.LESSER", "legal/GPL-3.0.txt", build.TEMPLATE):
            (copy / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, copy / name)
        shutil.copytree(REPO / build.PACKAGE, copy / build.PACKAGE,
                        ignore=shutil.ignore_patterns("__pycache__"))
        text = (copy / "pyproject.toml").read_text(encoding="utf-8")
        (copy / "pyproject.toml").write_text(
            text.replace('name = "exegete"', 'name = "some-other-name"', 1),
            encoding="utf-8")
        monkeypatch.setattr(build, "list_tools", lambda files: [])
        result = build.build(build.TreeSource(copy), tmp_path / "out")
        manifest = json.loads(
            (result["unpacked"] / "manifest.json").read_text(
                encoding="utf-8"))
        assert build.load_pyproject(build.TreeSource(copy))["project"][
            "name"] == "some-other-name"
        assert manifest["name"] == result["identifier"] == "qualcoder-mcp"
        assert smoke.extension_id(manifest) == \
            "local.mcpb.niccol-tempini.qualcoder-mcp"
        assert result["mcpb"].name == \
            f"exegete-{manifest['version']}.mcpb"
        assert result["unpacked"].name == f"exegete-{manifest['version']}"

    def test_the_build_names_its_files_from_the_stem(self):
        assert build.PACKAGE_FILE_STEM == names.DISTRIBUTION
        assert build.PACKAGE == f"src/{names.PACKAGE}"
