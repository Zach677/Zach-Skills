from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


SCRIPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "tuist-pr-upgrader"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import tuist_pr_upgrader  # type: ignore  # noqa: E402


SAMPLE_EXTEND = """
# Config

```toml
scan_roots = ["/tmp/repos"]
include_repos = ["mitori"]
exclude_repos = ["ignored"]
allow_push = false
allow_pr = false

[repos.mitori]
path = "/tmp/repos/mitori"
verify_commands = ["mise run test-macos"]
base_branch = "main"
```
"""


class ExtendConfigTests(unittest.TestCase):
    def test_extract_toml_block_returns_first_toml_fence(self) -> None:
        markdown = """
# Intro

```toml
allow_push = false
```

```toml
allow_push = true
```
"""

        result = tuist_pr_upgrader.extract_toml_block(markdown)

        self.assertEqual(result.strip(), 'allow_push = false')

    def test_configured_extend_file_paths_follow_project_xdg_user_order(self) -> None:
        project_dir = Path("/tmp/project-root")
        xdg_dir = Path("/tmp/xdg-home")
        user_dir = Path("/tmp/user-home")

        with mock.patch.object(tuist_pr_upgrader.Path, "cwd", return_value=project_dir):
            with mock.patch.object(tuist_pr_upgrader.Path, "home", return_value=user_dir):
                with mock.patch.dict(
                    tuist_pr_upgrader.os.environ,
                    {"XDG_CONFIG_HOME": str(xdg_dir)},
                    clear=False,
                ):
                    paths = tuist_pr_upgrader.configured_extend_file_paths()

        self.assertEqual(
            paths,
            (
                project_dir / ".zach-skills" / "tuist-pr-upgrader" / "EXTEND.md",
                xdg_dir / "zach-skills" / "tuist-pr-upgrader" / "EXTEND.md",
                user_dir / ".zach-skills" / "tuist-pr-upgrader" / "EXTEND.md",
            ),
        )

    def test_load_extend_config_parses_top_level_and_repo_values(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "EXTEND.md"
            path.write_text(SAMPLE_EXTEND, encoding="utf-8")

            config = tuist_pr_upgrader.load_extend_config(path)

        self.assertEqual(config.scan_roots, [Path("/tmp/repos").resolve()])
        self.assertEqual(config.include_repos, ["mitori"])
        self.assertEqual(config.exclude_repos, ["ignored"])
        self.assertFalse(config.allow_push)
        self.assertFalse(config.allow_pr)
        self.assertEqual(list(config.repos), ["mitori"])
        self.assertEqual(config.repos["mitori"].path, Path("/tmp/repos/mitori").resolve())
        self.assertEqual(config.repos["mitori"].verify_commands, ["mise run test-macos"])
        self.assertEqual(config.repos["mitori"].base_branch, "main")

    def test_load_extend_config_rejects_non_boolean_allow_flags(self) -> None:
        extend = """
# Config

```toml
scan_roots = ["/tmp/repos"]
allow_push = "false"
allow_pr = false
```
"""

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "EXTEND.md"
            path.write_text(extend, encoding="utf-8")

            with self.assertRaises(TypeError):
                tuist_pr_upgrader.load_extend_config(path)

    def test_load_extend_config_resolves_relative_paths_from_extend_file(self) -> None:
        extend = """
# Config

```toml
scan_roots = ["repos"]
allow_push = false
allow_pr = false

[repos.demo]
path = "repos/demo"
verify_commands = ["mise run test-macos"]
```
"""

        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "config"
            config_dir.mkdir()
            path = config_dir / "EXTEND.md"
            path.write_text(extend, encoding="utf-8")

            config = tuist_pr_upgrader.load_extend_config(path)

        self.assertEqual(config.scan_roots, [(config_dir / "repos").resolve()])
        self.assertEqual(config.repos["demo"].path, (config_dir / "repos" / "demo").resolve())

    def test_load_extend_config_canonicalizes_parent_relative_repo_paths(self) -> None:
        extend = """
# Config

```toml
scan_roots = ["../repos"]
allow_push = false
allow_pr = false

[repos.demo]
path = "../repos/demo"
verify_commands = ["mise run test-macos"]
```
"""

        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "config"
            config_dir.mkdir()
            path = config_dir / "EXTEND.md"
            path.write_text(extend, encoding="utf-8")

            config = tuist_pr_upgrader.load_extend_config(path)

        self.assertEqual(config.scan_roots, [(root / "repos").resolve()])
        self.assertEqual(config.repos["demo"].path, (root / "repos" / "demo").resolve())


class CandidateRepoTests(unittest.TestCase):
    def test_is_tuist_candidate_requires_project_tuist_and_mise_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "mitori"
            repo.mkdir()
            self.assertFalse(tuist_pr_upgrader.is_tuist_candidate(repo))

            (repo / "Project.swift").write_text("", encoding="utf-8")
            (repo / "Tuist.swift").write_text("", encoding="utf-8")
            self.assertFalse(tuist_pr_upgrader.is_tuist_candidate(repo))

            (repo / "mise.toml").write_text("", encoding="utf-8")
            self.assertTrue(tuist_pr_upgrader.is_tuist_candidate(repo))

    def test_discover_candidate_repos_returns_only_valid_candidates(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            valid_repo = root / "mitori"
            valid_repo.mkdir()
            for name in ("Project.swift", "Tuist.swift", "mise.toml"):
                (valid_repo / name).write_text("", encoding="utf-8")

            invalid_repo = root / "notes"
            invalid_repo.mkdir()
            (invalid_repo / "Project.swift").write_text("", encoding="utf-8")

            nested_repo = root / "apps" / "kigen"
            nested_repo.mkdir(parents=True)
            for name in ("Project.swift", "Tuist.swift", "mise.toml"):
                (nested_repo / name).write_text("", encoding="utf-8")

            discovered = tuist_pr_upgrader.discover_candidate_repos([root])

        self.assertEqual(discovered, [nested_repo.resolve(), valid_repo.resolve()])

    def test_discover_candidate_repos_returns_resolved_paths(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            repo = cwd / "repos" / "demo"
            repo.mkdir(parents=True)
            for name in ("Project.swift", "Tuist.swift", "mise.toml"):
                (repo / name).write_text("", encoding="utf-8")

            original_cwd = Path.cwd()
            os.chdir(cwd)
            try:
                discovered = tuist_pr_upgrader.discover_candidate_repos([Path("repos")])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(discovered, [repo.resolve()])


class PlanningTests(unittest.TestCase):
    def test_read_pinned_tuist_version_returns_configured_version(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "mise.toml"
            path.write_text('[tools]\ntuist = "4.162.1"\n', encoding="utf-8")

            version = tuist_pr_upgrader.read_pinned_tuist_version(path)

        self.assertEqual(version, "4.162.1")

    def test_read_pinned_tuist_version_ignores_keys_outside_tools_section(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "mise.toml"
            path.write_text(
                '[tasks.run]\ntuist = "fake-task-value"\n\n[tools]\ntuist = "4.162.1"\n',
                encoding="utf-8",
            )

            version = tuist_pr_upgrader.read_pinned_tuist_version(path)

        self.assertEqual(version, "4.162.1")

    def test_replace_pinned_tuist_version_updates_only_tuist_entry(self) -> None:
        text = '[tools]\npython = "3.13"\ntuist = "4.162.1"\n'

        updated = tuist_pr_upgrader.replace_pinned_tuist_version(text, "4.171.2")

        self.assertIn('python = "3.13"', updated)
        self.assertIn('tuist = "4.171.2"', updated)
        self.assertNotIn('tuist = "4.162.1"', updated)

    def test_replace_pinned_tuist_version_updates_tools_entry_only(self) -> None:
        text = (
            '[tasks.run]\ntuist = "fake-task-value"\n\n'
            '[tools]\npython = "3.13"\ntuist = "4.162.1"\n'
        )

        updated = tuist_pr_upgrader.replace_pinned_tuist_version(text, "4.171.2")

        self.assertIn('tuist = "fake-task-value"', updated)
        self.assertIn('[tools]\npython = "3.13"\ntuist = "4.171.2"', updated)

    def test_get_latest_tuist_version_uses_mise_latest(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["mise", "latest", "tuist"],
            returncode=0,
            stdout="4.171.2\n",
            stderr="",
        )

        with mock.patch.object(
            tuist_pr_upgrader.subprocess,
            "run",
            return_value=completed,
        ) as mocked_run:
            version = tuist_pr_upgrader.get_latest_tuist_version()

        self.assertEqual(version, "4.171.2")
        mocked_run.assert_called_once()

    def test_build_repo_plan_marks_up_to_date_repo(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "mitori"
            repo.mkdir()
            (repo / "mise.toml").write_text('[tools]\ntuist = "4.171.2"\n', encoding="utf-8")

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="mitori",
                    path=repo,
                    verify_commands=["mise run test-macos"],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "up-to-date")
        self.assertEqual(plan.current_version, "4.171.2")
        self.assertEqual(plan.target_version, "4.171.2")
        self.assertEqual(plan.suggested_verify_commands, [])

    def test_build_repo_plan_marks_repo_needing_upgrade(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "mitori"
            repo.mkdir()
            (repo / "mise.toml").write_text('[tools]\ntuist = "4.162.1"\n', encoding="utf-8")

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="mitori",
                    path=repo,
                    verify_commands=["mise run test-macos"],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "needs-upgrade")
        self.assertEqual(plan.current_version, "4.162.1")

    def test_build_repo_plan_skips_repo_without_verification_commands(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "mitori"
            repo.mkdir()
            (repo / "mise.toml").write_text(
                '[tools]\ntuist = "4.162.1"\n\n[tasks.test-macos]\nrun = "bash test.sh"\n',
                encoding="utf-8",
            )

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="mitori",
                    path=repo,
                    verify_commands=[],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "skipped-missing-verification")
        self.assertEqual(plan.suggested_verify_commands, ["mise run test-macos"])

    def test_build_repo_plan_keeps_current_repo_up_to_date_without_verification(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "mitori"
            repo.mkdir()
            (repo / "mise.toml").write_text('[tools]\ntuist = "4.171.2"\n', encoding="utf-8")

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="mitori",
                    path=repo,
                    verify_commands=[],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "up-to-date")
        self.assertEqual(plan.suggested_verify_commands, [])

    def test_build_repo_plan_prefers_config_error_over_missing_verification(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "broken"
            repo.mkdir()
            (repo / "mise.toml").write_text('[tools]\npython = "3.13"\n', encoding="utf-8")

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="broken",
                    path=repo,
                    verify_commands=[],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "skipped-config-error")
        self.assertEqual(plan.suggested_verify_commands, [])

    def test_build_repo_plan_marks_invalid_mise_as_config_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "broken"
            repo.mkdir()
            (repo / "mise.toml").write_text('[tools]\npython = "3.13"\n', encoding="utf-8")

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="broken",
                    path=repo,
                    verify_commands=["mise run test-macos"],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "skipped-config-error")
        self.assertIsNone(plan.current_version)

    def test_build_repo_plan_marks_missing_mise_file_as_config_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir) / "missing"
            repo.mkdir()

            plan = tuist_pr_upgrader.build_repo_plan(
                tuist_pr_upgrader.RepoConfig(
                    name="missing",
                    path=repo,
                    verify_commands=["mise run test-macos"],
                ),
                target_version="4.171.2",
            )

        self.assertEqual(plan.status, "skipped-config-error")
        self.assertIsNone(plan.current_version)

    def test_render_plan_report_includes_suggested_verify_commands(self) -> None:
        plan = tuist_pr_upgrader.RepoPlan(
            name="mitori",
            path=Path("/tmp/mitori"),
            current_version="4.162.1",
            target_version="4.171.2",
            status="skipped-missing-verification",
            reason="verify commands are missing",
            verify_commands=[],
            suggested_verify_commands=["mise run test-macos"],
        )

        report = tuist_pr_upgrader.render_plan_report([plan])

        self.assertIn("mitori", report)
        self.assertIn("skipped-missing-verification", report)
        self.assertIn("mise run test-macos", report)


if __name__ == "__main__":
    unittest.main()
