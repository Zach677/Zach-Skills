from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import tomllib


EXTEND_SKILL_NAME = "tuist-pr-upgrader"
TOML_FENCE_RE = re.compile(r"```toml\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
REQUIRED_REPO_FILES = ("Project.swift", "Tuist.swift", "mise.toml")
SECTION_HEADER_RE = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")
TUIST_ASSIGNMENT_RE = re.compile(r'^(?P<prefix>\s*tuist\s*=\s*")(?P<version>[^"]+)(?P<suffix>".*)$')


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


@dataclass
class RepoPlan:
    name: str
    path: Path
    current_version: str | None
    target_version: str | None
    status: str
    reason: str | None
    verify_commands: list[str]
    suggested_verify_commands: list[str]


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


def get_latest_tuist_version() -> str:
    completed = subprocess.run(
        ["mise", "latest", "tuist"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def read_pinned_tuist_version(mise_toml_path: Path) -> str | None:
    if not mise_toml_path.exists():
        return None
    current_section: str | None = None
    for line in mise_toml_path.read_text(encoding="utf-8").splitlines():
        section_match = SECTION_HEADER_RE.match(line)
        if section_match is not None:
            current_section = section_match.group("section").strip()
            continue
        if current_section != "tools":
            continue
        assignment_match = TUIST_ASSIGNMENT_RE.match(line)
        if assignment_match is not None:
            return assignment_match.group("version")
    return None


def replace_pinned_tuist_version(text: str, version: str) -> str:
    current_section: str | None = None
    updated_lines: list[str] = []
    replaced = False

    for line in text.splitlines():
        section_match = SECTION_HEADER_RE.match(line)
        if section_match is not None:
            current_section = section_match.group("section").strip()
            updated_lines.append(line)
            continue

        if not replaced and current_section == "tools":
            assignment_match = TUIST_ASSIGNMENT_RE.match(line)
            if assignment_match is not None:
                updated_lines.append(
                    f'{assignment_match.group("prefix")}{version}{assignment_match.group("suffix")}'
                )
                replaced = True
                continue

        updated_lines.append(line)

    if not replaced:
        raise ValueError("mise.toml does not contain a pinned tools.tuist version")

    trailing_newline = "\n" if text.endswith("\n") else ""
    return "\n".join(updated_lines) + trailing_newline


def suggest_verify_commands(repo_path: Path) -> list[str]:
    mise_toml_path = repo_path / "mise.toml"
    if mise_toml_path.exists():
        content = mise_toml_path.read_text(encoding="utf-8")
        if "test-macos" in content:
            return ["mise run test-macos"]
        if "run-macos" in content:
            return ["mise run run-macos"]
    return ["mise exec -- tuist generate --no-open"]


def build_repo_plan(repo_config: RepoConfig, target_version: str) -> RepoPlan:
    current_version = read_pinned_tuist_version(repo_config.path / "mise.toml")

    if current_version is None:
        return RepoPlan(
            name=repo_config.name,
            path=repo_config.path,
            current_version=None,
            target_version=target_version,
            status="skipped-config-error",
            reason="pinned tuist version is missing",
            verify_commands=repo_config.verify_commands,
            suggested_verify_commands=[],
        )

    if current_version == target_version:
        return RepoPlan(
            name=repo_config.name,
            path=repo_config.path,
            current_version=current_version,
            target_version=target_version,
            status="up-to-date",
            reason=None,
            verify_commands=repo_config.verify_commands,
            suggested_verify_commands=[],
        )

    if not repo_config.verify_commands:
        return RepoPlan(
            name=repo_config.name,
            path=repo_config.path,
            current_version=current_version,
            target_version=target_version,
            status="skipped-missing-verification",
            reason="verify commands are missing",
            verify_commands=[],
            suggested_verify_commands=suggest_verify_commands(repo_config.path),
        )

    return RepoPlan(
        name=repo_config.name,
        path=repo_config.path,
        current_version=current_version,
        target_version=target_version,
        status="needs-upgrade",
        reason="pinned tuist version differs from target",
        verify_commands=repo_config.verify_commands,
        suggested_verify_commands=[],
    )


def render_plan_report(plans: list[RepoPlan]) -> str:
    lines = ["# Tuist Upgrade Plan", ""]
    for plan in plans:
        lines.append(f"- `{plan.name}`: `{plan.status}`")
        if plan.current_version is not None or plan.target_version is not None:
            lines.append(
                f"  current: `{plan.current_version or 'missing'}` -> target: `{plan.target_version or 'missing'}`"
            )
        if plan.reason:
            lines.append(f"  reason: {plan.reason}")
        if plan.verify_commands:
            lines.append(f"  verify: {', '.join(plan.verify_commands)}")
        if plan.suggested_verify_commands:
            lines.append(f"  suggested verify: {', '.join(plan.suggested_verify_commands)}")
    return "\n".join(lines)


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
