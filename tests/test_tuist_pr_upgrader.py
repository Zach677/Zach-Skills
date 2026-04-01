from __future__ import annotations

import os
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


if __name__ == "__main__":
    unittest.main()
