import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "bin" / "zach-mobile-init"


class ZachMobileInitTests(unittest.TestCase):
    def run_cli(self, config, expect_success=True):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as temp_config:
            json.dump(config, temp_config)
            temp_config.flush()
        try:
            process = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--config", temp_config.name],
                capture_output=True,
                text=True,
            )
            if expect_success:
                self.assertEqual(
                    process.returncode,
                    0,
                    msg=f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}",
                )
            else:
                self.assertNotEqual(process.returncode, 0)
            return process
        finally:
            os.unlink(temp_config.name)

    def build_config(self, template_source, destination, **overrides):
        base = {
            "mode": "local-only",
            "template": "ios",
            "template_source_path": str(template_source),
            "destination_path": str(destination),
            "destination_strategy": "create",
            "project_name": "SubPanda",
            "repo_name": "subpanda",
            "owner": "zach",
            "full_handle": "zach/subpanda",
            "bundle_id": "org.zach.subpanda",
            "ios_simulator_device": "iPhone 16",
            "visibility": "private",
            "create_initial_commit": False,
            "push_after_init": False,
            "setup_tuist_cloud": False,
            "setup_tuist_cache": False,
        }
        base.update(overrides)
        return base

    def create_template(self, path, include_unknown=False):
        path.mkdir(parents=True, exist_ok=True)
        (path / "__PROJECT_NAME__.txt").write_text(
            "Project __PROJECT_NAME__ lower __PROJECT_NAME_LOWER__ bundle __BUNDLE_ID__ handle __FULL_HANDLE__"
        )
        (path / "details.md").write_text(
            "Device __IOS_SIMULATOR_DEVICE__ app __APP_SCHEME__ tests __TEST_SCHEME__ cache __CACHE_SERVICE_SLUG__"
        )
        data_assets = path / "__PROJECT_NAME__-assets"
        data_assets.mkdir()
        (data_assets / "info.md").write_text(
            "Cache slug __CACHE_SERVICE_SLUG__, handle __FULL_HANDLE__, and slug again __CACHE_SERVICE_SLUG__"
        )
        if include_unknown:
            (data_assets / "mystery.md").write_text("Please replace __WHATEVER__")
        scripts = path / "scripts"
        scripts.mkdir()
        script_file = scripts / "run-ios-sim.sh"
        script_file.write_text("#!/bin/bash\necho __PROJECT_NAME__")
        script_file.chmod(0o644)
        workspace = path / "__PROJECT_NAME__-workspace.xcworkspace"
        workspace.mkdir()
        (workspace / "contents.xcworkspacedata").write_text("workspace __FULL_HANDLE__")

    def test_replaces_placeholders_and_normalizes_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            self.create_template(template_dir)
            config = self.build_config(template_dir, destination)
            process = self.run_cli(config)
            self.assertIn('"status": "ok"', process.stdout)

            renamed_file = destination / "SubPanda.txt"
            self.assertTrue(renamed_file.exists())
            content = renamed_file.read_text()
            self.assertIn("Project SubPanda lower subpanda", content)
            self.assertIn("bundle org.zach.subpanda", content)
            assets_dir = destination / "SubPanda-assets"
            self.assertTrue(assets_dir.is_dir())
            info_text = (assets_dir / "info.md").read_text()
            self.assertIn("zach-subpanda", info_text)
            workspace = destination / "SubPanda-workspace.xcworkspace"
            self.assertTrue(workspace.is_dir())
            scheme = workspace / "contents.xcworkspacedata"
            self.assertIn("zach/subpanda", scheme.read_text())
            script = destination / "scripts" / "run-ios-sim.sh"
            self.assertTrue(script.exists())
            self.assertTrue(os.access(script, os.X_OK))

    def test_derives_full_handle_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            self.create_template(template_dir)
            config = self.build_config(template_dir, destination, full_handle=None)
            config.pop("full_handle", None)
            process = self.run_cli(config)
            self.assertIn("zach/subpanda", (destination / "SubPanda-assets" / "info.md").read_text())

    def test_local_only_does_not_require_owner_repo_or_visibility(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            self.create_template(template_dir)
            config = self.build_config(template_dir, destination)
            config.pop("owner", None)
            config.pop("repo_name", None)
            config.pop("visibility", None)
            config.pop("full_handle", None)
            process = self.run_cli(config)
            self.assertIn('"full_handle": "local/subpanda"', process.stdout)

    def test_rejects_unknown_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            self.create_template(template_dir)
            config = self.build_config(template_dir, destination, template="dark")
            process = self.run_cli(config, expect_success=False)
            self.assertIn("template", process.stderr.lower())

    def test_rejects_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            self.create_template(template_dir)
            config = self.build_config(template_dir, destination)
            del config["bundle_id"]
            process = self.run_cli(config, expect_success=False)
            self.assertIn("bundle_id", process.stderr)

    def test_fails_when_placeholders_remain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            self.create_template(template_dir, include_unknown=True)
            config = self.build_config(template_dir, destination)
            process = self.run_cli(config, expect_success=False)
            self.assertIn("__WHATEVER__", process.stderr)

    def test_create_strategy_rejects_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir) / "template"
            destination = Path(tmpdir) / "out"
            destination.mkdir()
            self.create_template(template_dir)
            config = self.build_config(template_dir, destination)
            process = self.run_cli(config, expect_success=False)
            self.assertIn("already exists", process.stderr.lower())
