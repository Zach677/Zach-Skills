#!/usr/bin/env python3
"""Shared orchestration helpers for create-tuist-mobile-project."""

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

ChoiceQuestionID = Literal[
    "mode",
    "template",
    "visibility",
    "destination_strategy",
    "create_tuist_cloud_project",
    "setup_tuist_cache",
    "create_initial_commit",
    "push_after_init",
    "repo_exists_resolution",
    "full_handle_exists_resolution",
]

TextQuestionID = Literal[
    "project_name",
    "destination_path",
    "owner",
    "repo_name",
    "bundle_id",
    "ios_simulator_device",
    "full_handle",
]

InterviewQuestionID = ChoiceQuestionID | TextQuestionID

RepoExistsResolution = Literal["choose-another", "switch-to-local-only", "abort"]
FullHandleExistsResolution = Literal["bind-existing", "choose-another", "abort"]


class InteractiveOption(TypedDict):
    value: str
    label: str
    description: str
    availability: Literal["available", "blocked"]
    blocked_reason: NotRequired[str]


class InteractiveChoiceQuestion(TypedDict):
    id: ChoiceQuestionID
    header: str
    prompt: str
    options: list[InteractiveOption]


class InteractiveTextQuestion(TypedDict):
    id: TextQuestionID
    header: str
    prompt: str
    default: NotRequired[str]
    required: bool


class CodexTextFallbackQuestion(TypedDict):
    header: str
    prompt: str
    default: NotRequired[str]


class ClaudeCodeAskUserQuestion(TypedDict):
    prompt: str


class InterviewState(TypedDict, total=False):
    mode: Literal["local-only", "github-backed", "github-and-tuist-cloud"]
    template: Literal["ios", "ios-catalyst"]
    project_name: str
    destination_path: str
    destination_exists: bool
    destination_strategy: Literal["create", "reuse", "replace", "abort"]
    owner: str
    repo_name: str
    repo_exists: bool
    repo_exists_resolution: RepoExistsResolution
    visibility: Literal["private", "public"]
    bundle_id: str
    ios_simulator_device: str
    create_tuist_cloud_project: bool
    setup_tuist_cache: bool
    full_handle: str
    full_handle_exists: bool
    full_handle_exists_resolution: FullHandleExistsResolution
    create_initial_commit: bool
    push_after_init: bool
    aborted: bool


class RequestUserInputOption(TypedDict):
    label: str
    description: str


class RequestUserInputQuestion(TypedDict):
    header: str
    id: str
    question: str
    options: list[RequestUserInputOption]


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


MODE_LABELS: dict[str, str] = {
    "local-only": "Local Only",
    "github-backed": "GitHub Backed",
    "github-and-tuist-cloud": "GitHub + Tuist Cloud",
}


def build_mode_question(capabilities: List[CapabilityStatus]) -> InteractiveChoiceQuestion:
    blockers = describe_mode_blockers(capabilities)
    options: list[InteractiveOption] = []
    for mode in ("local-only", "github-backed", "github-and-tuist-cloud"):
        mode_blockers = blockers[mode]
        option: InteractiveOption = {
            "value": mode,
            "label": MODE_LABELS[mode],
            "description": "available" if not mode_blockers else f"blocked by: {', '.join(mode_blockers)}",
            "availability": "available" if not mode_blockers else "blocked",
        }
        if mode_blockers:
            option["blocked_reason"] = ", ".join(mode_blockers)
        options.append(option)

    return {
        "id": "mode",
        "header": "Mode",
        "prompt": "Choose the project creation mode.",
        "options": options,
    }


def build_template_question() -> InteractiveChoiceQuestion:
    return {
        "id": "template",
        "header": "Template",
        "prompt": "Choose the starter template shape.",
        "options": [
            {
                "value": "ios",
                "label": "Pure iOS",
                "description": "Create an iPhone-first Tuist app starter.",
                "availability": "available",
            },
            {
                "value": "ios-catalyst",
                "label": "iOS + Catalyst",
                "description": "Create a shared iOS and Mac Catalyst starter.",
                "availability": "available",
            },
        ],
    }


def build_visibility_question() -> InteractiveChoiceQuestion:
    return {
        "id": "visibility",
        "header": "Visibility",
        "prompt": "Choose the GitHub repository visibility.",
        "options": [
            {
                "value": "private",
                "label": "Private",
                "description": "Only invited collaborators can access it.",
                "availability": "available",
            },
            {
                "value": "public",
                "label": "Public",
                "description": "Anyone can view and clone it.",
                "availability": "available",
            },
        ],
    }


def build_destination_strategy_question(path_label: str) -> InteractiveChoiceQuestion:
    return {
        "id": "destination_strategy",
        "header": "Directory",
        "prompt": f"`{path_label}` already exists. Choose how to proceed.",
        "options": [
            {
                "value": "reuse",
                "label": "Reuse",
                "description": "Keep the directory and write into it.",
                "availability": "available",
            },
            {
                "value": "replace",
                "label": "Replace",
                "description": "Delete the directory contents and recreate it.",
                "availability": "available",
            },
            {
                "value": "abort",
                "label": "Abort",
                "description": "Stop here without writing anything.",
                "availability": "available",
            },
        ],
    }


def build_confirmation_question(
    question_id: Literal[
        "create_tuist_cloud_project",
        "setup_tuist_cache",
        "create_initial_commit",
        "push_after_init",
    ],
    header: str,
    prompt: str,
    *,
    yes_label: str = "Yes",
    no_label: str = "No",
) -> InteractiveChoiceQuestion:
    return {
        "id": question_id,
        "header": header,
        "prompt": prompt,
        "options": [
            {
                "value": "yes",
                "label": yes_label,
                "description": "Proceed with this step.",
                "availability": "available",
            },
            {
                "value": "no",
                "label": no_label,
                "description": "Skip this step.",
                "availability": "available",
            },
        ],
    }


def build_repo_exists_resolution_question(owner: str, repo_name: str) -> InteractiveChoiceQuestion:
    return {
        "id": "repo_exists_resolution",
        "header": "Repo Exists",
        "prompt": f"`{owner}/{repo_name}` already exists on GitHub. Choose how to proceed.",
        "options": [
            {
                "value": "choose-another",
                "label": "Choose Another Name",
                "description": "Enter a different repository name.",
                "availability": "available",
            },
            {
                "value": "switch-to-local-only",
                "label": "Switch to Local Only",
                "description": "Skip GitHub creation and keep the run local.",
                "availability": "available",
            },
            {
                "value": "abort",
                "label": "Abort",
                "description": "Stop here without creating anything else.",
                "availability": "available",
            },
        ],
    }


def build_full_handle_exists_resolution_question(full_handle: str) -> InteractiveChoiceQuestion:
    return {
        "id": "full_handle_exists_resolution",
        "header": "Handle Exists",
        "prompt": f"`{full_handle}` already exists in Tuist Cloud. Choose how to proceed.",
        "options": [
            {
                "value": "bind-existing",
                "label": "Bind Existing",
                "description": "Use the existing Tuist Cloud handle.",
                "availability": "available",
            },
            {
                "value": "choose-another",
                "label": "Choose Another Handle",
                "description": "Enter a different full handle.",
                "availability": "available",
            },
            {
                "value": "abort",
                "label": "Abort",
                "description": "Stop here without creating anything else.",
                "availability": "available",
            },
        ],
    }


def build_text_question(
    question_id: TextQuestionID,
    header: str,
    prompt: str,
    *,
    default: str | None = None,
) -> InteractiveTextQuestion:
    question: InteractiveTextQuestion = {
        "id": question_id,
        "header": header,
        "prompt": prompt,
        "required": True,
    }
    if default is not None:
        question["default"] = default
    return question


def can_render_request_user_input(question: InteractiveChoiceQuestion) -> bool:
    return all(option["availability"] == "available" for option in question["options"])


def to_request_user_input_question(question: InteractiveChoiceQuestion) -> RequestUserInputQuestion:
    blocked = [option for option in question["options"] if option["availability"] != "available"]
    if blocked:
        blocked_labels = ", ".join(option["label"] for option in blocked)
        raise ValueError(
            f"Question '{question['id']}' has blocked options and cannot be rendered as request_user_input: {blocked_labels}."
        )

    return {
        "header": question["header"],
        "id": question["id"],
        "question": question["prompt"],
        "options": [
            {
                "label": option["label"],
                "description": option["description"],
            }
            for option in question["options"]
        ],
    }


def to_codex_text_fallback_question(question: InteractiveTextQuestion) -> CodexTextFallbackQuestion:
    fallback: CodexTextFallbackQuestion = {
        "header": question["header"],
        "prompt": question["prompt"],
    }
    if "default" in question:
        fallback["default"] = question["default"]
    return fallback


def _recommended_choice(question: InteractiveChoiceQuestion) -> InteractiveOption | None:
    for option in question["options"]:
        if option["availability"] == "available":
            return option
    return None


def to_claude_code_ask_user_question(
    question: InteractiveChoiceQuestion | InteractiveTextQuestion,
    *,
    project_label: str,
    branch: str,
    task_label: str,
) -> ClaudeCodeAskUserQuestion:
    lines = [
        f"Project: {project_label}",
        f"Branch: {branch}",
        f"Task: {task_label}",
        "",
        f"{question['header']}: {question['prompt']}",
    ]

    if "options" in question:
        recommended = _recommended_choice(question)
        if recommended is not None:
            lines.extend(
                [
                    "",
                    f"RECOMMENDATION: Choose {recommended['label']} because it is the first available path.",
                    "",
                    "Options:",
                ]
            )
        else:
            lines.extend(["", "Options:"])

        for index, option in enumerate(question["options"]):
            letter = chr(ord("A") + index)
            suffix = (
                f" ({option['availability']}: {option.get('blocked_reason', option['description'])})"
                if option["availability"] == "blocked"
                else f" ({option['description']})"
            )
            lines.append(f"{letter}) {option['label']}{suffix}")
    else:
        if "default" in question:
            lines.append("")
            lines.append(f"Default: {question['default']}")
        lines.append("")
        lines.append("Reply with one value only.")

    return {"prompt": "\n".join(lines)}


def apply_choice_answer(state: InterviewState, question_id: ChoiceQuestionID, value: str) -> InterviewState:
    next_state: InterviewState = {**state}

    if question_id in {"mode", "template", "visibility", "destination_strategy"}:
        next_state[question_id] = value  # type: ignore[index]
        return next_state

    if question_id in {"create_tuist_cloud_project", "setup_tuist_cache", "create_initial_commit", "push_after_init"}:
        next_state[question_id] = value == "yes"  # type: ignore[index]
        if question_id == "create_initial_commit" and value != "yes":
            next_state.pop("push_after_init", None)
        return next_state

    if question_id == "repo_exists_resolution":
        if value == "choose-another":
            next_state.pop("repo_name", None)
            next_state["repo_exists"] = False
        elif value == "switch-to-local-only":
            next_state["mode"] = "local-only"
            for key in (
                "owner",
                "repo_name",
                "repo_exists",
                "visibility",
                "create_tuist_cloud_project",
                "setup_tuist_cache",
                "full_handle",
                "full_handle_exists",
                "push_after_init",
            ):
                next_state.pop(key, None)
        elif value == "abort":
            next_state["aborted"] = True
        return next_state

    if question_id == "full_handle_exists_resolution":
        if value == "choose-another":
            next_state.pop("full_handle", None)
            next_state["full_handle_exists"] = False
        elif value == "bind-existing":
            next_state["full_handle_exists"] = False
        elif value == "abort":
            next_state["aborted"] = True
        return next_state

    return next_state


def apply_text_answer(state: InterviewState, question_id: TextQuestionID, value: str) -> InterviewState:
    next_state: InterviewState = {**state}
    next_state[question_id] = value  # type: ignore[index]
    return next_state


def next_interview_question(
    *,
    capabilities: List[CapabilityStatus],
    state: InterviewState,
    tuist_owner: str | None = None,
) -> InteractiveChoiceQuestion | InteractiveTextQuestion | None:
    if state.get("aborted"):
        return None

    if "mode" not in state:
        return build_mode_question(capabilities)
    if "template" not in state:
        return build_template_question()
    if "project_name" not in state:
        return build_text_question("project_name", "Project Name", "Choose the project name.")
    if "destination_path" not in state:
        return build_text_question(
            "destination_path",
            "Destination",
            "Choose the destination path.",
            default=str(Path(".").resolve() / state["project_name"]),
        )
    if state.get("destination_exists") and "destination_strategy" not in state:
        return build_destination_strategy_question(state["destination_path"])

    if state["mode"] != "local-only":
        if "owner" not in state:
            return build_text_question("owner", "GitHub Owner", "Choose the GitHub owner.")
        if "repo_name" not in state:
            return build_text_question(
                "repo_name",
                "Repository Name",
                "Choose the GitHub repository name.",
                default=Path(state["project_name"]).name.lower().replace(" ", "-"),
            )
        if state.get("repo_exists"):
            return build_repo_exists_resolution_question(state["owner"], state["repo_name"])
        if "visibility" not in state:
            return build_visibility_question()

    if "bundle_id" not in state:
        slug = Path(state["project_name"]).name.lower().replace(" ", "")
        return build_text_question(
            "bundle_id",
            "Bundle Identifier",
            "Choose the app bundle identifier.",
            default=f"com.example.{slug}",
        )
    if "ios_simulator_device" not in state:
        return build_text_question(
            "ios_simulator_device",
            "Simulator",
            "Choose the default iOS simulator device.",
            default="iPhone 16",
        )

    if state["mode"] == "github-and-tuist-cloud":
        if "create_tuist_cloud_project" not in state:
            return build_confirmation_question(
                "create_tuist_cloud_project",
                "Tuist Cloud",
                "Create a Tuist Cloud project?",
            )
        if "setup_tuist_cache" not in state:
            return build_confirmation_question(
                "setup_tuist_cache",
                "Tuist Cache",
                "Run `tuist setup cache` after initialization?",
            )
        if state.get("create_tuist_cloud_project") or state.get("setup_tuist_cache"):
            if "full_handle" not in state:
                owner = tuist_owner or state.get("owner") or "local"
                repo = state.get("repo_name") or Path(state["project_name"]).name.lower().replace(" ", "-")
                return build_text_question(
                    "full_handle",
                    "Tuist Handle",
                    "Choose the Tuist Cloud full handle.",
                    default=f"{owner}/{repo}",
                )
            if state.get("full_handle_exists"):
                return build_full_handle_exists_resolution_question(state["full_handle"])

    if "create_initial_commit" not in state:
        return build_confirmation_question(
            "create_initial_commit",
            "Git",
            "Create the initial commit?",
        )
    if state.get("create_initial_commit") and state["mode"] != "local-only" and "push_after_init" not in state:
        return build_confirmation_question(
            "push_after_init",
            "Git",
            "Push the initial commit after setup?",
        )
    return None


def build_codex_interaction_question(
    *,
    capabilities: List[CapabilityStatus],
    state: InterviewState,
    tuist_owner: str | None = None,
) -> RequestUserInputQuestion | None:
    question = next_interview_question(capabilities=capabilities, state=state, tuist_owner=tuist_owner)
    if question is None or "options" not in question:
        return None
    if not can_render_request_user_input(question):
        return None
    return to_request_user_input_question(question)


def build_claude_interaction_prompt(
    *,
    capabilities: List[CapabilityStatus],
    state: InterviewState,
    project_label: str,
    branch: str,
    task_label: str,
    tuist_owner: str | None = None,
) -> str | None:
    question = next_interview_question(capabilities=capabilities, state=state, tuist_owner=tuist_owner)
    if question is None:
        return None
    return to_claude_code_ask_user_question(
        question,
        project_label=project_label,
        branch=branch,
        task_label=task_label,
    )["prompt"]


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
