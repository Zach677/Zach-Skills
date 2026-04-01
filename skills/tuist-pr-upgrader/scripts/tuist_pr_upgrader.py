from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib


EXTEND_SKILL_NAME = "tuist-pr-upgrader"
TOML_FENCE_RE = re.compile(r"```toml\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
REQUIRED_REPO_FILES = ("Project.swift", "Tuist.swift", "mise.toml")


@dataclass
class RepoConfig:
    name: str
    path: Path
    verify_commands: list[str]
    base_branch: str | None = None


@dataclass
class ExtendConfig:
    scan_roots: list[Path]
    include_repos: list[str]
    exclude_repos: list[str]
    allow_push: bool
    allow_pr: bool
    repos: dict[str, RepoConfig]


def configured_extend_file_paths() -> tuple[Path, Path, Path]:
    project_root = Path.cwd()
    home = Path.home()
    xdg_root = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return (
        project_root / ".zach-skills" / EXTEND_SKILL_NAME / "EXTEND.md",
        xdg_root / "zach-skills" / EXTEND_SKILL_NAME / "EXTEND.md",
        home / ".zach-skills" / EXTEND_SKILL_NAME / "EXTEND.md",
    )


def extract_toml_block(markdown: str) -> str:
    match = TOML_FENCE_RE.search(markdown)
    if match is None:
        raise ValueError("EXTEND.md must contain a fenced toml block")
    return match.group(1).strip()


def load_extend_config(path: Path) -> ExtendConfig:
    payload = tomllib.loads(extract_toml_block(path.read_text(encoding="utf-8")))
    base_dir = path.parent
    repos_payload = payload.get("repos", {})
    repos: dict[str, RepoConfig] = {}
    for name, repo_payload in repos_payload.items():
        repos[name] = RepoConfig(
            name=name,
            path=resolve_config_path(repo_payload["path"], base_dir),
            verify_commands=expect_string_list(
                repo_payload.get("verify_commands", []),
                f"repos.{name}.verify_commands",
            ),
            base_branch=expect_optional_string(
                repo_payload.get("base_branch"),
                f"repos.{name}.base_branch",
            ),
        )

    return ExtendConfig(
        scan_roots=[
            resolve_config_path(item, base_dir)
            for item in expect_string_list(payload.get("scan_roots", []), "scan_roots")
        ],
        include_repos=expect_string_list(payload.get("include_repos", []), "include_repos"),
        exclude_repos=expect_string_list(payload.get("exclude_repos", []), "exclude_repos"),
        allow_push=expect_bool(payload.get("allow_push", False), "allow_push"),
        allow_pr=expect_bool(payload.get("allow_pr", False), "allow_pr"),
        repos=repos,
    )


def is_tuist_candidate(path: Path) -> bool:
    return path.is_dir() and all((path / filename).is_file() for filename in REQUIRED_REPO_FILES)


def discover_candidate_repos(scan_roots: list[Path]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    for scan_root in scan_roots:
        resolved_root = scan_root.resolve()
        if not resolved_root.exists():
            continue
        for current_root, dirnames, _filenames in os.walk(resolved_root):
            current_path = Path(current_root)
            if is_tuist_candidate(current_path):
                resolved = current_path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    discovered.append(resolved)
                dirnames[:] = []

    return sorted(discovered)


def expect_bool(value: object, key: str) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError(f"{key} must be a boolean")


def expect_optional_string(value: object, key: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise TypeError(f"{key} must be a string")


def expect_string_list(value: object, key: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError(f"{key} must be a list of strings")
    return list(value)


def resolve_config_path(raw_path: object, base_dir: Path) -> Path:
    if not isinstance(raw_path, str):
        raise TypeError("config paths must be strings")
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()
