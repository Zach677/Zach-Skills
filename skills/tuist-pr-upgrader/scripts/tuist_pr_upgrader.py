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
    repos_payload = payload.get("repos", {})
    repos: dict[str, RepoConfig] = {}
    for name, repo_payload in repos_payload.items():
        repos[name] = RepoConfig(
            name=name,
            path=Path(repo_payload["path"]),
            verify_commands=list(repo_payload.get("verify_commands", [])),
            base_branch=repo_payload.get("base_branch"),
        )

    return ExtendConfig(
        scan_roots=[Path(item) for item in payload.get("scan_roots", [])],
        include_repos=list(payload.get("include_repos", [])),
        exclude_repos=list(payload.get("exclude_repos", [])),
        allow_push=bool(payload.get("allow_push", False)),
        allow_pr=bool(payload.get("allow_pr", False)),
        repos=repos,
    )


def is_tuist_candidate(path: Path) -> bool:
    return path.is_dir() and all((path / filename).is_file() for filename in REQUIRED_REPO_FILES)


def discover_candidate_repos(scan_roots: list[Path]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for current_root, dirnames, _filenames in os.walk(scan_root):
            current_path = Path(current_root)
            if is_tuist_candidate(current_path):
                resolved = current_path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    discovered.append(current_path)
                dirnames[:] = []

    return sorted(discovered)
