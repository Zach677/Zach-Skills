#!/usr/bin/env python3
"""Shared orchestration helper shells for bootstrap-tuist-mobile-project."""

from dataclasses import dataclass
from typing import List, Literal, NotRequired, TypedDict


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


def detect_capabilities() -> List[CapabilityStatus]:
    """Check GitHub, Tuist, and helper tooling availability."""

    # Task 1 only defines the future helper surface. Later tasks implement
    # the actual capability checks here so the skill can call into one
    # deterministic helper layer.
    raise NotImplementedError("Task 1 shell only: capability detection helper is not implemented yet.")


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
) -> BootstrapPayload:
    """Build the JSON payload that `bin/zach-mobile-init` consumes."""

    # Task 1 only defines the future helper surface. Later tasks will make
    # this function assemble the exact initializer payload so the skill does
    # not hand-roll JSON contracts inline.
    raise NotImplementedError("Task 1 shell only: payload assembly is not implemented yet.")


def collect_approvals() -> ApprovalSet:
    """Collect the fixed approval set for later orchestration logic."""

    # Task 1 only defines the future helper surface. Later tasks will wire
    # this to the skill's explicit confirmation flow for the fixed set of
    # side effects: repo creation, Tuist Cloud setup, cache setup, commits,
    # and push, preserving one explicit answer per side effect.
    raise NotImplementedError("Task 1 shell only: approval collection helper is not implemented yet.")
