from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
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


@dataclass
class RepoRunResult:
    name: str
    status: str
    branch: str | None
    pr_url: str | None
    summary: str


@dataclass
class CliContext:
    extend_path: Path | None
    config: ExtendConfig | None


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


def configured_extend_file_paths() -> tuple[Path, Path, Path]:
    project_root = Path.cwd()
    home = Path.home()
    raw_xdg = os.environ.get("XDG_CONFIG_HOME", "")
    xdg_root = Path(raw_xdg.strip()) if raw_xdg.strip() else home / ".config"
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
    if not isinstance(repos_payload, Mapping):
        raise TypeError("repos must be a table of repo entries")
    repos: dict[str, RepoConfig] = {}
    for name, repo_payload in repos_payload.items():
        if not isinstance(repo_payload, Mapping):
            raise TypeError(f"repos.{name} must be a table")
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
    try:
        completed = subprocess.run(
            ["mise", "latest", "tuist"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("`mise` is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("`mise latest tuist` timed out") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() if exc.stderr else "`mise latest tuist` failed"
        raise RuntimeError(message) from exc
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
    lines: list[str] = []
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


def render_run_report(results: list[RepoRunResult], *, target_version: str) -> str:
    lines = ["# Tuist Upgrade Run", "", f"target version: `{target_version}`", ""]
    for result in results:
        lines.append(f"- `{result.name}`: `{result.status}`")
        if result.branch:
            lines.append(f"  branch: `{result.branch}`")
        if result.pr_url:
            lines.append(f"  pr: {result.pr_url}")
        lines.append(f"  summary: {result.summary}")
    return "\n".join(lines)


def filtered_repo_items(config: ExtendConfig) -> list[tuple[str, RepoConfig]]:
    included = set(config.include_repos)
    excluded = set(config.exclude_repos)
    items: list[tuple[str, RepoConfig]] = []
    for name, repo_config in sorted(config.repos.items()):
        if included and name not in included:
            continue
        if name in excluded:
            continue
        items.append((name, repo_config))
    return items


def run_command(
    args: list[str] | str,
    *,
    cwd: Path,
    check: bool = True,
    shell: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        shell=shell,
        capture_output=True,
        text=True,
    )


def git_worktree_is_clean(repo: Path) -> bool:
    completed = run_command(["git", "status", "--short"], cwd=repo)
    return completed.stdout.strip() == ""


def resolve_base_branch(repo: Path, configured: str | None) -> str:
    if configured:
        return configured
    completed = run_command(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"], cwd=repo)
    return completed.stdout.strip().removeprefix("origin/")


def existing_pr_for_version(repo: Path, version: str, base_branch: str) -> str | None:
    completed = run_command(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--base",
            base_branch,
            "--json",
            "title,url",
        ],
        cwd=repo,
        check=False,
    )
    if completed.returncode != 0:
        message = f"failed to query existing pull requests (exit {completed.returncode})"
        if completed.stderr:
            message += f": {completed.stderr.strip()}"
        raise RuntimeError(message)
    if not completed.stdout.strip():
        return None
    for item in json.loads(completed.stdout):
        if item.get("title") == f"chore: bump Tuist to {version}":
            return item.get("url")
    return None


def build_branch_name(version: str) -> str:
    return f"chore/tuist-{version.replace('.', '-')}"


def build_pr_body(repo_plan: RepoPlan) -> str:
    lines = [
        f"Current version: `{repo_plan.current_version or 'missing'}`",
        f"Target version: `{repo_plan.target_version or 'missing'}`",
    ]
    if repo_plan.verify_commands:
        lines.append("")
        lines.append("Verification:")
        for command in repo_plan.verify_commands:
            lines.append(f"- `{command}`")
    return "\n".join(lines)


def run_verification_commands(repo: Path, commands: list[str]) -> None:
    for command in commands:
        run_command(command, cwd=repo, shell=True)


def run_repo_upgrade(
    repo_config: RepoConfig,
    *,
    target_version: str,
    allow_push: bool,
    allow_pr: bool,
    dry_run: bool,
) -> RepoRunResult:
    if not dry_run and not git_worktree_is_clean(repo_config.path):
        return RepoRunResult(
            name=repo_config.name,
            status="skipped-dirty-worktree",
            branch=None,
            pr_url=None,
            summary="git worktree is dirty",
        )

    current_version = read_pinned_tuist_version(repo_config.path / "mise.toml")
    if current_version is None:
        return RepoRunResult(
            name=repo_config.name,
            status="skipped-config-error",
            branch=None,
            pr_url=None,
            summary="pinned tuist version is missing",
        )

    branch_name = build_branch_name(target_version)

    if dry_run:
        return RepoRunResult(
            name=repo_config.name,
            status="dry-run",
            branch=branch_name,
            pr_url=None,
            summary=f"would update {current_version} -> {target_version}",
        )

    base_branch = resolve_base_branch(repo_config.path, repo_config.base_branch)

    run_command(["git", "fetch", "origin"], cwd=repo_config.path)
    try:
        pr_url = existing_pr_for_version(repo_config.path, target_version, base_branch)
    except RuntimeError:
        return RepoRunResult(
            name=repo_config.name,
            status="skipped-config-error",
            branch=None,
            pr_url=None,
            summary="failed to query existing pull requests",
        )
    if pr_url is not None:
        return RepoRunResult(
            name=repo_config.name,
            status="skipped-existing-pr",
            branch=None,
            pr_url=pr_url,
            summary="existing PR found",
        )

    run_command(["git", "switch", base_branch], cwd=repo_config.path)
    run_command(["git", "pull", "--ff-only", "origin", base_branch], cwd=repo_config.path)
    run_command(["git", "switch", "-C", branch_name], cwd=repo_config.path)

    mise_toml_path = repo_config.path / "mise.toml"
    updated_mise_toml = replace_pinned_tuist_version(
        mise_toml_path.read_text(encoding="utf-8"),
        target_version,
    )
    mise_toml_path.write_text(updated_mise_toml, encoding="utf-8")

    try:
        run_verification_commands(repo_config.path, repo_config.verify_commands)
    except subprocess.CalledProcessError as exc:
        return RepoRunResult(
            name=repo_config.name,
            status="verification-failed",
            branch=branch_name,
            pr_url=None,
            summary=f"verification failed: {exc.cmd} returned {exc.returncode}",
        )

    run_command(["git", "add", "mise.toml"], cwd=repo_config.path)
    run_command(
        ["git", "commit", "-m", f"chore: bump Tuist to {target_version}"],
        cwd=repo_config.path,
    )

    created_pr_url: str | None = None
    if allow_push:
        run_command(["git", "push", "-u", "origin", branch_name], cwd=repo_config.path)

    if allow_pr and allow_push:
        repo_plan = RepoPlan(
            name=repo_config.name,
            path=repo_config.path,
            current_version=current_version,
            target_version=target_version,
            status="needs-upgrade",
            reason=None,
            verify_commands=repo_config.verify_commands,
            suggested_verify_commands=[],
        )
        completed = run_command(
            [
                "gh",
                "pr",
                "create",
                "--base",
                base_branch,
                "--head",
                branch_name,
                "--title",
                f"chore: bump Tuist to {target_version}",
                "--body",
                build_pr_body(repo_plan),
            ],
            cwd=repo_config.path,
        )
        created_pr_url = completed.stdout.strip() or None

    return RepoRunResult(
        name=repo_config.name,
        status="updated",
        branch=branch_name,
        pr_url=created_pr_url,
        summary=f"updated {current_version} -> {target_version}",
    )


def find_extend_path(explicit_path: str | None) -> Path | None:
    if explicit_path is not None:
        return Path(explicit_path).expanduser()
    for candidate in configured_extend_file_paths():
        if candidate.exists():
            return candidate
    return None


def load_cli_context(explicit_path: str | None) -> CliContext:
    extend_path = find_extend_path(explicit_path)
    if extend_path is None or not extend_path.exists():
        return CliContext(extend_path=extend_path, config=None)
    return CliContext(extend_path=extend_path, config=load_extend_config(extend_path))


def command_scan(args: argparse.Namespace) -> int:
    context = load_cli_context(args.extend)
    if context.config is None:
        print("# Tuist Upgrade Scan\n\nNo EXTEND.md found. Report-only mode.")
        return 0

    candidates = discover_candidate_repos(context.config.scan_roots)
    lines = ["# Tuist Upgrade Scan", ""]
    lines.append(f"config: `{context.extend_path}`")
    lines.append("")
    lines.append("candidates:")
    for candidate in candidates:
        lines.append(f"- `{candidate}`")
    lines.append("")
    lines.append("configured repos:")
    for name, repo_config in filtered_repo_items(context.config):
        lines.append(f"- `{name}`: `{repo_config.path}`")
    print("\n".join(lines))
    return 0


def command_plan(args: argparse.Namespace) -> int:
    context = load_cli_context(args.extend)
    if context.config is None:
        print("# Tuist Upgrade Plan\n\nNo EXTEND.md found. Report-only mode.")
        return 0

    try:
        target_version = get_latest_tuist_version()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    scanned_repos = discover_candidate_repos(context.config.scan_roots)
    plans = [
        build_repo_plan(repo_config, target_version)
        for _, repo_config in filtered_repo_items(context.config)
    ]

    lines = ["# Tuist Upgrade Plan", "", f"target version: `{target_version}`", ""]
    lines.append("scanned repos:")
    for repo in scanned_repos:
        lines.append(f"- `{repo}`")
    lines.append("")
    lines.append(render_plan_report(plans))
    print("\n".join(lines))
    return 0


def command_run(args: argparse.Namespace) -> int:
    context = load_cli_context(args.extend)
    if context.config is None:
        print("# Tuist Upgrade Run\n\nNo EXTEND.md found. Report-only mode.")
        return 0

    try:
        target_version = get_latest_tuist_version()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    results: list[RepoRunResult] = []

    for _, repo_config in filtered_repo_items(context.config):
        plan = build_repo_plan(repo_config, target_version)
        if plan.status == "needs-upgrade":
            try:
                results.append(
                    run_repo_upgrade(
                        repo_config,
                        target_version=target_version,
                        allow_push=context.config.allow_push,
                        allow_pr=context.config.allow_pr,
                        dry_run=args.dry_run,
                    )
                )
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                results.append(
                    RepoRunResult(
                        name=repo_config.name,
                        status="skipped-config-error",
                        branch=None,
                        pr_url=None,
                        summary=str(exc),
                    )
                )
            continue

        results.append(
            RepoRunResult(
                name=repo_config.name,
                status=plan.status,
                branch=None,
                pr_url=None,
                summary=plan.reason or "no action required",
            )
        )

    print(render_run_report(results, target_version=target_version))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan, plan, and run Tuist upgrade workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Discover configured Tuist repositories.")
    scan_parser.add_argument("--extend", help="Path to EXTEND.md")
    scan_parser.set_defaults(func=command_scan)

    plan_parser = subparsers.add_parser("plan", help="Build an upgrade plan for configured repos.")
    plan_parser.add_argument("--extend", help="Path to EXTEND.md")
    plan_parser.set_defaults(func=command_plan)

    run_parser = subparsers.add_parser("run", help="Execute or dry-run the upgrade workflow.")
    run_parser.add_argument("--extend", help="Path to EXTEND.md")
    run_parser.add_argument("--dry-run", action="store_true", help="Report actions without mutating repos.")
    run_parser.set_defaults(func=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
