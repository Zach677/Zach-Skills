#!/usr/bin/env python3
"""Shared orchestration helpers for bootstrap-tuist-mobile-project."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Literal, NotRequired, Sequence, TypedDict


@dataclass(frozen=True)
class CapabilityStatus:
    name: str
    state: Literal["available", "unauthenticated", "missing"]
    detail: str


class BootstrapPayload(TypedDict):
    mode: Literal["local-only", "github-backed", "github-and-tuist-cloud"]
    template: Literal["ios", "ios-catalyst"]
    template_source_path: str
    destination_path: str
    destination_strategy: Literal["create", "reuse", "replace", "abort"]
    project_name: str
    repo_name: NotRequired[str]
    owner: NotRequired[str]
    bundle_id: str
    full_handle: NotRequired[str]
    cache_service_slug: NotRequired[str]
    visibility: NotRequired[Literal["private", "public"]]
    ios_simulator_device: str
    app_scheme: NotRequired[str]
    test_scheme: NotRequired[str]
    create_initial_commit: bool
    push_after_init: bool
    setup_tuist_cloud: bool
    setup_tuist_cache: bool

ConfirmationDecision = Literal["confirmed", "declined", "not_asked"]


class ApprovalSet(TypedDict):
    create_github_repo: ConfirmationDecision
    create_tuist_cloud_project: ConfirmationDecision
    setup_tuist_cache: ConfirmationDecision
    create_initial_commit: ConfirmationDecision
    push_after_init: ConfirmationDecision


ApprovalKey = Literal[
    "create_github_repo",
    "create_tuist_cloud_project",
    "setup_tuist_cache",
    "create_initial_commit",
    "push_after_init",
]


CAPABILITY_CHECKS: Sequence[tuple[str, Sequence[str]]] = (
    ("git", ("git", "--version")),
    ("gh", ("gh", "--version")),
    ("gh auth status", ("gh", "auth", "status")),
    ("mise", ("mise", "--version")),
    ("tuist", ("mise", "exec", "--", "tuist", "version")),
    ("tuist auth whoami", ("mise", "exec", "--", "tuist", "auth", "whoami")),
)

MODE_REQUIREMENTS: dict[str, list[str]] = {
    "local-only": ["git", "mise", "tuist"],
    "github-backed": ["git", "mise", "tuist", "gh", "gh auth status"],
    "github-and-tuist-cloud": [
        "git",
        "mise",
        "tuist",
        "gh",
        "gh auth status",
        "tuist auth whoami",
    ],
}


GIT_COMMIT_MESSAGE = "Initial commit"


def _run_check(command: Sequence[str], *, cwd: Path | None) -> tuple[str, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd is not None else None,
        )
    except FileNotFoundError as exc:
        return "missing", f"{command[0]}: {exc}"

    detail = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return "available", detail or "available"
    return "unauthenticated", detail or "command returned non-zero"


def detect_capabilities(repo_root: str | Path | None = None) -> List[CapabilityStatus]:
    """Check GitHub, Tuist, and helper tooling availability."""

    cwd = Path(repo_root).expanduser() if repo_root is not None else None
    statuses: list[CapabilityStatus] = []
    for name, command in CAPABILITY_CHECKS:
        state, detail = _run_check(command, cwd=cwd)
        statuses.append(CapabilityStatus(name=name, state=state, detail=detail))
    return statuses


def _run_command(command: Sequence[str], *, cwd: Path | None = None) -> None:
    subprocess.run(
        command,
        check=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def create_github_repo(owner: str, repo_name: str, visibility: str) -> None:
    flag = f"--{visibility}" if visibility in {"public", "private"} else "--private"
    _run_command(
        ["gh", "repo", "create", f"{owner}/{repo_name}", flag, "--confirm"],
    )


def tuist_project_create(destination: Path, full_handle: str) -> None:
    _run_command(
        ["mise", "exec", "--", "tuist", "project", "create", full_handle, "--build-system", "xcode"],
        cwd=destination,
    )


def tuist_setup_cache(destination: Path) -> None:
    _run_command(
        ["mise", "exec", "--", "tuist", "setup", "cache", "--path", str(destination)],
        cwd=destination,
    )


def warm_external_cache(destination: Path) -> None:
    _run_command(
        ["mise", "run", "warm-external-cache"],
        cwd=destination,
    )


def mise_trust(mise_toml_path: Path) -> None:
    _run_command(
        ["mise", "trust", str(mise_toml_path)],
    )


def git_init(destination: Path) -> None:
    _run_command(["git", "init"], cwd=destination)


def git_add(destination: Path) -> None:
    _run_command(["git", "add", "-A"], cwd=destination)


def git_commit(destination: Path, message: str = GIT_COMMIT_MESSAGE) -> None:
    _run_command(["git", "commit", "-m", message], cwd=destination)


def git_push(destination: Path) -> None:
    _run_command(["git", "push", "-u", "origin", "HEAD"], cwd=destination)


def git_remote_add(destination: Path, remote_name: str, remote_url: str) -> None:
    _run_command(["git", "remote", "add", remote_name, remote_url], cwd=destination)


class _DefaultExecutor:
    def create_github_repo(self, owner: str, repo_name: str, visibility: str) -> None:
        create_github_repo(owner, repo_name, visibility)

    def tuist_project_create(self, destination: Path, full_handle: str) -> None:
        tuist_project_create(destination, full_handle)

    def tuist_setup_cache(self, destination: Path) -> None:
        tuist_setup_cache(destination)

    def warm_external_cache(self, destination: Path) -> None:
        warm_external_cache(destination)

    def mise_trust(self, mise_toml_path: Path) -> None:
        mise_trust(mise_toml_path)

    def git_init(self, destination: Path) -> None:
        git_init(destination)

    def git_add(self, destination: Path) -> None:
        git_add(destination)

    def git_commit(self, destination: Path, message: str) -> None:
        git_commit(destination, message)

    def git_push(self, destination: Path) -> None:
        git_push(destination)

    def git_remote_add(self, destination: Path, remote_name: str, remote_url: str) -> None:
        git_remote_add(destination, remote_name, remote_url)


def _approval_is_confirmed(approvals: ApprovalSet, key: ApprovalKey, action: str) -> bool:
    state = approvals[key]
    if state == "not_asked":
        raise ValueError(f"{action} requires explicit approval; current state is {state}.")
    return state == "confirmed"


def _normalize_approvals_for_mode(mode: str, approvals: ApprovalSet) -> ApprovalSet:
    normalized = {**approvals}
    if mode == "local-only":
        normalized.update(
            {
                "create_github_repo": "declined",
                "create_tuist_cloud_project": "declined",
                "setup_tuist_cache": "declined",
                "push_after_init": "declined",
            }
        )
    elif mode == "github-backed":
        normalized.update(
            {
                "create_tuist_cloud_project": "declined",
                "setup_tuist_cache": "declined",
            }
        )

    if normalized["create_initial_commit"] != "confirmed":
        normalized["push_after_init"] = "declined"
    return normalized


def execute_side_effects(
    *,
    payload: BootstrapPayload,
    approvals: ApprovalSet,
    destination_path: str | Path,
    executor: _DefaultExecutor | None = None,
) -> None:
    target = Path(destination_path).expanduser().resolve()
    executor = executor or _DefaultExecutor()
    approvals = _normalize_approvals_for_mode(payload["mode"], approvals)
    mise_toml_path = target / "mise.toml"

    if mise_toml_path.exists():
        executor.mise_trust(mise_toml_path)

    if payload["mode"] != "local-only":
        if _approval_is_confirmed(approvals, "create_github_repo", "GitHub repo creation"):
            owner = payload.get("owner")
            repo_name = payload.get("repo_name")
            if not owner or not repo_name:
                raise ValueError("GitHub owner and repo name are required.")
            visibility = payload.get("visibility", "private")
            executor.create_github_repo(owner, repo_name, visibility)

    full_handle = payload.get("full_handle")

    if _approval_is_confirmed(
        approvals, "create_tuist_cloud_project", "Tuist Cloud project creation"
    ):
        if not full_handle:
            raise ValueError("Tuist Cloud creation requires a full_handle.")
        executor.tuist_project_create(target, full_handle)

    if _approval_is_confirmed(approvals, "setup_tuist_cache", "Tuist Xcode cache setup"):
        if not full_handle:
            raise ValueError("Tuist Xcode cache setup requires a full_handle.")
        executor.tuist_setup_cache(target)

    executor.warm_external_cache(target)

    commit_confirmed = _approval_is_confirmed(
        approvals, "create_initial_commit", "initial commit creation"
    )

    if commit_confirmed:
        executor.git_init(target)
        if payload["mode"] != "local-only":
            owner = payload.get("owner")
            repo_name = payload.get("repo_name")
            if not owner or not repo_name:
                raise ValueError("GitHub owner and repo name are required.")
            executor.git_remote_add(target, "origin", f"https://github.com/{owner}/{repo_name}.git")
        executor.git_add(target)
        executor.git_commit(target, GIT_COMMIT_MESSAGE)
        if _approval_is_confirmed(approvals, "push_after_init", "push after initial commit"):
            executor.git_push(target)

def build_payload(
    *,
    mode: Literal["local-only", "github-backed", "github-and-tuist-cloud"],
    template: Literal["ios", "ios-catalyst"],
    template_source_path: str,
    destination_path: str,
    destination_strategy: Literal["create", "reuse", "replace", "abort"],
    project_name: str,
    bundle_id: str,
    ios_simulator_device: str,
    approvals: ApprovalSet,
    owner: str | None = None,
    repo_name: str | None = None,
    full_handle: str | None = None,
    cache_service_slug: str | None = None,
    visibility: Literal["private", "public"] | None = None,
    app_scheme: str | None = None,
    test_scheme: str | None = None,
) -> BootstrapPayload:
    """Build the JSON payload that `bin/zach-mobile-init` consumes."""

    approvals = _normalize_approvals_for_mode(mode, approvals)

    unresolved = [name for name, state in approvals.items() if state == "not_asked"]
    if unresolved:
        raise ValueError(f"Approvals are unresolved: {', '.join(unresolved)}")

    should_configure_tuist_cloud = (
        approvals["create_tuist_cloud_project"] == "confirmed"
        or approvals["setup_tuist_cache"] == "confirmed"
    )

    if full_handle is None and should_configure_tuist_cloud and owner and repo_name:
        full_handle = f"{owner}/{repo_name}"

    if cache_service_slug is None and full_handle:
        cache_service_slug = full_handle.replace("/", "-")

    payload: BootstrapPayload = {
        "mode": mode,
        "template": template,
        "template_source_path": template_source_path,
        "destination_path": destination_path,
        "destination_strategy": destination_strategy,
        "project_name": project_name,
        "bundle_id": bundle_id,
        "ios_simulator_device": ios_simulator_device,
        "create_initial_commit": approvals["create_initial_commit"] == "confirmed",
        "push_after_init": approvals["push_after_init"] == "confirmed",
        "setup_tuist_cloud": approvals["create_tuist_cloud_project"] == "confirmed",
        "setup_tuist_cache": approvals["setup_tuist_cache"] == "confirmed",
    }

    if owner:
        payload["owner"] = owner
    if repo_name:
        payload["repo_name"] = repo_name
    if visibility:
        payload["visibility"] = visibility
    if full_handle:
        payload["full_handle"] = full_handle
    if cache_service_slug:
        payload["cache_service_slug"] = cache_service_slug
    if app_scheme:
        payload["app_scheme"] = app_scheme
    if test_scheme:
        payload["test_scheme"] = test_scheme

    return payload


def collect_approvals() -> ApprovalSet:
    """Collect the fixed approval set for later orchestration logic."""

    return {
        "create_github_repo": "not_asked",
        "create_tuist_cloud_project": "not_asked",
        "setup_tuist_cache": "not_asked",
        "create_initial_commit": "not_asked",
        "push_after_init": "not_asked",
    }


def describe_mode_blockers(capabilities: List[CapabilityStatus]) -> dict[str, list[str]]:
    state_map = {cap.name: cap.state for cap in capabilities}
    blockers: dict[str, list[str]] = {}
    for mode, requirements in MODE_REQUIREMENTS.items():
        missing = [name for name in requirements if state_map.get(name) != "available"]
        blockers[mode] = missing
    return blockers


def describe_mode_messages(capabilities: List[CapabilityStatus]) -> dict[str, str]:
    messages: dict[str, str] = {}
    for mode, blockers in describe_mode_blockers(capabilities).items():
        if not blockers:
            messages[mode] = "available"
            continue
        messages[mode] = f"blocked by: {', '.join(blockers)}"
    return messages


def ensure_mode_capabilities(mode: str, capabilities: List[CapabilityStatus]) -> None:
    blockers = describe_mode_blockers(capabilities).get(mode, [])
    if blockers:
        raise ValueError(f"The mode '{mode}' is blocked by missing capabilities: {', '.join(blockers)}")


def require_confirmed_approval(approvals: ApprovalSet, key: ApprovalKey, action: str) -> None:
    state = approvals[key]
    if state != "confirmed":
        raise ValueError(f"{action} requires explicit approval; current state is {state}.")
