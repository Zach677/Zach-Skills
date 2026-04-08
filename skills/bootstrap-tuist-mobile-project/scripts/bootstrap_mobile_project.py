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

    if mode == "local-only":
        approvals = {
            **approvals,
            "create_github_repo": "declined",
            "create_tuist_cloud_project": "declined",
            "setup_tuist_cache": "declined",
        }
    elif mode == "github-backed":
        approvals = {
            **approvals,
            "create_tuist_cloud_project": "declined",
            "setup_tuist_cache": "declined",
        }

    if approvals["create_initial_commit"] != "confirmed":
        approvals = {
            **approvals,
            "push_after_init": "declined",
        }

    unresolved = [name for name, state in approvals.items() if state == "not_asked"]
    if unresolved:
        raise ValueError(f"Approvals are unresolved: {', '.join(unresolved)}")

    if full_handle is None and owner and repo_name:
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
