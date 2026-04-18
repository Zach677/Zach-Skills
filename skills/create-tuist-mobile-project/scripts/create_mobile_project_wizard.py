#!/usr/bin/env python3
"""Interactive terminal wizard for create-tuist-mobile-project."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Sequence, TextIO

import create_mobile_project as cmp


ChoiceValue = str
InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]

TEMPLATE_REMOTE_URLS = {
    "ios": "https://github.com/Zach677/tuist-ios-starter.git",
    "ios-catalyst": "https://github.com/Zach677/tuist-ios-catalyst-starter.git",
}


@dataclass
class WizardDependencies:
    detect_capabilities: Callable[[str | Path | None], list[cmp.CapabilityStatus]]
    build_payload: Callable[..., cmp.BootstrapPayload]
    execute_side_effects: Callable[..., None]
    initializer_path: Path
    ios_template_path: Path | None = None
    ios_catalyst_template_path: Path | None = None

    def github_repo_exists(self, owner: str, repo_name: str) -> bool:
        result = subprocess.run(
            ["gh", "repo", "view", f"{owner}/{repo_name}", "--json", "name"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def full_handle_exists(self, full_handle: str) -> bool:
        result = subprocess.run(
            ["zsh", "-lc", f"mise exec -- tuist project show {full_handle!s} >/dev/null 2>&1"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def clone_template(self, template: str) -> tuple[Path, TemporaryDirectory | None]:
        override = self.ios_template_path if template == "ios" else self.ios_catalyst_template_path
        if override is not None:
            return override.expanduser().resolve(), None

        tempdir = TemporaryDirectory(prefix=f"create-tuist-mobile-project-{template}-")
        target = Path(tempdir.name) / "template"
        subprocess.run(
            ["git", "clone", "--depth", "1", TEMPLATE_REMOTE_URLS[template], str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
        return target, tempdir

    def run_initializer(self, payload: cmp.BootstrapPayload) -> dict:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as config_file:
            config_path = Path(config_file.name)
            json.dump(payload, config_file)

        try:
            result = subprocess.run(
                [sys.executable, str(self.initializer_path), "--config", str(config_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            config_path.unlink(missing_ok=True)

        return json.loads(result.stdout)


def default_dependencies(repo_root: Path) -> WizardDependencies:
    return WizardDependencies(
        detect_capabilities=cmp.detect_capabilities,
        build_payload=cmp.build_payload,
        execute_side_effects=cmp.execute_side_effects,
        initializer_path=repo_root / "bin" / "zach-mobile-init",
    )


def slugify_project_name(project_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")
    return slug or "app"


def validate_project_name(value: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]*", value):
        return "Use letters, numbers, spaces, hyphens, or underscores, and start with a letter or number."
    return None


def validate_repo_owner(value: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9-]+", value):
        return "GitHub owner can only contain letters, numbers, and hyphens."
    return None


def validate_repo_name(value: str) -> str | None:
    if not re.fullmatch(r"[a-z0-9._-]+", value):
        return "Repository name should use lowercase letters, numbers, dots, underscores, or hyphens."
    return None


def validate_bundle_id(value: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", value):
        return "Bundle identifier should look like com.example.app."
    return None


def validate_full_handle(value: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9-]+", value):
        return "Full handle should look like account/project."
    return None


def detect_tuist_cloud_owner(capabilities: Sequence[cmp.CapabilityStatus]) -> str | None:
    for capability in capabilities:
        if capability.name == "tuist auth whoami" and capability.state == "available":
            line = capability.detail.strip().splitlines()[0].strip()
            return line or None
    return None


def format_capability_summary(capabilities: Sequence[cmp.CapabilityStatus]) -> list[str]:
    return [f"- {capability.name}: {capability.state}" for capability in capabilities]


def prompt_choice(
    question: cmp.InteractiveChoiceQuestion,
    *,
    input_fn: InputFn,
    output_fn: OutputFn,
) -> ChoiceValue:
    options = question["options"]
    index_map = {chr(ord("A") + idx): option for idx, option in enumerate(options)}

    while True:
        output_fn(f"{question['header']}: {question['prompt']}")
        for label, option in index_map.items():
            suffix = (
                f" [{option['availability']}: {option.get('blocked_reason', option['description'])}]"
                if option["availability"] == "blocked"
                else f" [{option['description']}]"
            )
            output_fn(f"  {label}. {option['label']}{suffix}")

        raw = input_fn("> ").strip()
        if not raw:
            output_fn("Enter one option.")
            continue

        normalized = raw.lower()
        selected = None
        for label, option in index_map.items():
            if normalized in {label.lower(), option["value"], option["label"].lower()}:
                selected = option
                break

        if selected is None:
            output_fn("That choice is not valid.")
            continue
        if selected["availability"] != "available":
            output_fn(f"'{selected['label']}' is blocked: {selected.get('blocked_reason', 'unavailable')}")
            continue
        return selected["value"]


def prompt_text(
    prompt: str,
    *,
    input_fn: InputFn,
    output_fn: OutputFn,
    default: str | None = None,
    validator: Callable[[str], str | None] | None = None,
) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input_fn(f"{prompt}{suffix}: ").strip()
        if not value and default is not None:
            value = default
        if not value:
            output_fn("This value is required.")
            continue
        if validator is not None:
            error = validator(value)
            if error:
                output_fn(error)
                continue
        return value


def prompt_confirmation(
    header: str,
    prompt: str,
    *,
    input_fn: InputFn,
    output_fn: OutputFn,
    default_yes: bool = False,
) -> bool:
    default_hint = "Y/n" if default_yes else "y/N"
    while True:
        answer = input_fn(f"{header}: {prompt} [{default_hint}] ").strip().lower()
        if not answer:
            return default_yes
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        output_fn("Answer yes or no.")


def resolve_choice_value(
    question: cmp.InteractiveChoiceQuestion,
    raw_value: str,
) -> cmp.InteractiveOption:
    normalized = raw_value.strip().lower()
    for index, option in enumerate(question["options"]):
        letter = chr(ord("A") + index).lower()
        if normalized in {letter, option["value"], option["label"].lower()}:
            return option
    raise ValueError(f"'{raw_value}' is not a valid choice for {question['id']}.")


def choose_or_prompt(
    question: cmp.InteractiveChoiceQuestion,
    *,
    prefilled: str | bool | None,
    input_fn: InputFn,
    output_fn: OutputFn,
    non_interactive: bool,
) -> str:
    if isinstance(prefilled, bool):
        prefilled_value = "yes" if prefilled else "no"
    else:
        prefilled_value = prefilled

    if prefilled_value is not None:
        option = resolve_choice_value(question, str(prefilled_value))
        if option["availability"] != "available":
            raise ValueError(
                f"Choice '{prefilled_value}' for {question['id']} is blocked: {option.get('blocked_reason', 'unavailable')}."
            )
        return option["value"]

    if non_interactive:
        raise ValueError(f"Missing required choice for {question['id']} in non-interactive mode.")

    return prompt_choice(question, input_fn=input_fn, output_fn=output_fn)


def text_or_prompt(
    prompt: str,
    *,
    prefilled: str | None,
    input_fn: InputFn,
    output_fn: OutputFn,
    default: str | None = None,
    validator: Callable[[str], str | None] | None = None,
    non_interactive: bool,
) -> str:
    if prefilled is not None:
        if validator is not None:
            error = validator(prefilled)
            if error:
                raise ValueError(error)
        return prefilled

    if non_interactive:
        if default is not None:
            return default
        raise ValueError(f"Missing required value for '{prompt}' in non-interactive mode.")

    return prompt_text(
        prompt,
        input_fn=input_fn,
        output_fn=output_fn,
        default=default,
        validator=validator,
    )


def build_destination_default(cwd: Path, project_name: str) -> Path:
    return cwd / project_name


def run_wizard(
    *,
    cwd: Path,
    repo_root: Path,
    input_fn: InputFn = input,
    output_stream: TextIO = sys.stdout,
    dependencies: WizardDependencies | None = None,
    prefilled: cmp.InterviewState | None = None,
    non_interactive: bool = False,
) -> int:
    dependencies = dependencies or default_dependencies(repo_root)
    output_fn = lambda line: print(line, file=output_stream)
    prefilled = dict(prefilled or {})

    capabilities = dependencies.detect_capabilities(cwd)
    output_fn("Capabilities:")
    for line in format_capability_summary(capabilities):
        output_fn(line)

    mode = choose_or_prompt(
        cmp.build_mode_question(capabilities),
        prefilled=prefilled.get("mode"),
        input_fn=input_fn,
        output_fn=output_fn,
        non_interactive=non_interactive,
    )
    cmp.ensure_mode_capabilities(mode, capabilities)

    template = choose_or_prompt(
        cmp.build_template_question(),
        prefilled=prefilled.get("template"),
        input_fn=input_fn,
        output_fn=output_fn,
        non_interactive=non_interactive,
    )

    project_name = text_or_prompt(
        "Project name",
        prefilled=prefilled.get("project_name"),
        input_fn=input_fn,
        output_fn=output_fn,
        validator=validate_project_name,
        non_interactive=non_interactive,
    )
    destination_default = str(build_destination_default(cwd, project_name).expanduser())
    destination_path = Path(
        text_or_prompt(
            "Destination path",
            prefilled=prefilled.get("destination_path"),
            input_fn=input_fn,
            output_fn=output_fn,
            default=destination_default,
            non_interactive=non_interactive,
        )
    ).expanduser()

    destination_strategy: Literal["create", "reuse", "replace", "abort"] = "create"
    if destination_path.exists():
        destination_strategy = choose_or_prompt(
            cmp.build_destination_strategy_question(str(destination_path)),
            prefilled=prefilled.get("destination_strategy"),
            input_fn=input_fn,
            output_fn=output_fn,
            non_interactive=non_interactive,
        )
        if destination_strategy == "abort":
            output_fn("Aborted before writing files.")
            return 1

    owner = None
    repo_name = None
    visibility = None
    full_handle = None
    bound_existing_full_handle = False
    create_tuist_cloud = False
    setup_tuist_cache = False
    tuist_owner = detect_tuist_cloud_owner(capabilities)

    if mode != "local-only":
        owner = text_or_prompt(
            "GitHub owner",
            prefilled=prefilled.get("owner"),
            input_fn=input_fn,
            output_fn=output_fn,
            validator=validate_repo_owner,
            non_interactive=non_interactive,
        )
        while True:
            repo_name = text_or_prompt(
                "Repository name",
                prefilled=prefilled.get("repo_name"),
                input_fn=input_fn,
                output_fn=output_fn,
                default=slugify_project_name(project_name),
                validator=validate_repo_name,
                non_interactive=non_interactive,
            )
            if not dependencies.github_repo_exists(owner, repo_name):
                break

            output_fn(f"`{owner}/{repo_name}` already exists on GitHub.")
            if non_interactive:
                raise ValueError(f"`{owner}/{repo_name}` already exists on GitHub.")
            if prompt_confirmation(
                "GitHub",
                "Choose another repository name?",
                input_fn=input_fn,
                output_fn=output_fn,
                default_yes=True,
            ):
                continue

            fallback = prompt_choice(
                {
                    "id": "destination_strategy",
                    "header": "Repo Exists",
                    "prompt": "The requested repo already exists. Choose how to proceed.",
                    "options": [
                        {
                            "value": "switch-to-local-only",
                            "label": "Switch to Local Only",
                            "description": "Skip GitHub creation and keep this run local.",
                            "availability": "available",
                        },
                        {
                            "value": "abort",
                            "label": "Abort",
                            "description": "Stop here without creating anything else.",
                            "availability": "available",
                        },
                    ],
                },
                input_fn=input_fn,
                output_fn=output_fn,
            )
            if fallback == "abort":
                output_fn("Aborted before writing files.")
                return 1
            mode = "local-only"
            owner = None
            repo_name = None
            visibility = None
            break

        if mode != "local-only":
            visibility = choose_or_prompt(
                cmp.build_visibility_question(),
                prefilled=prefilled.get("visibility"),
                input_fn=input_fn,
                output_fn=output_fn,
                non_interactive=non_interactive,
            )

    bundle_id = text_or_prompt(
        "Bundle identifier",
        prefilled=prefilled.get("bundle_id"),
        input_fn=input_fn,
        output_fn=output_fn,
        default=f"com.example.{slugify_project_name(project_name)}",
        validator=validate_bundle_id,
        non_interactive=non_interactive,
    )
    ios_simulator_device = text_or_prompt(
        "Default iOS simulator device",
        prefilled=prefilled.get("ios_simulator_device"),
        input_fn=input_fn,
        output_fn=output_fn,
        default="iPhone 16",
        non_interactive=non_interactive,
    )

    if mode == "github-and-tuist-cloud":
        create_tuist_cloud = choose_or_prompt(
            cmp.build_confirmation_question(
                "create_tuist_cloud_project",
                "Tuist Cloud",
                "Create a Tuist Cloud project?",
            ),
            prefilled=prefilled.get("create_tuist_cloud_project"),
            input_fn=input_fn,
            output_fn=output_fn,
            non_interactive=non_interactive,
        ) == "yes"
        if create_tuist_cloud:
            suggested_owner = tuist_owner or owner or "local"
            full_handle = text_or_prompt(
                "Tuist full handle",
                prefilled=prefilled.get("full_handle"),
                input_fn=input_fn,
                output_fn=output_fn,
                default=f"{suggested_owner}/{repo_name}",
                validator=validate_full_handle,
                non_interactive=non_interactive,
            )
            while dependencies.full_handle_exists(full_handle):
                output_fn(f"`{full_handle}` already exists in Tuist Cloud.")
                if non_interactive:
                    raise ValueError(f"`{full_handle}` already exists in Tuist Cloud.")
                resolution = prompt_choice(
                    cmp.build_full_handle_exists_resolution_question(full_handle),
                    input_fn=input_fn,
                    output_fn=output_fn,
                )
                if resolution == "bind-existing":
                    create_tuist_cloud = False
                    bound_existing_full_handle = True
                    break
                if resolution == "abort":
                    output_fn("Aborted before writing files.")
                    return 1
                full_handle = prompt_text(
                    "Tuist full handle",
                    input_fn=input_fn,
                    output_fn=output_fn,
                    default=f"{suggested_owner}/{repo_name}",
                    validator=validate_full_handle,
                    non_interactive=non_interactive,
                )
        setup_tuist_cache = choose_or_prompt(
            cmp.build_confirmation_question(
                "setup_tuist_cache",
                "Tuist Cache",
                "Run `tuist setup cache` after initialization?",
            ),
            prefilled=prefilled.get("setup_tuist_cache"),
            input_fn=input_fn,
            output_fn=output_fn,
            non_interactive=non_interactive,
        ) == "yes"
        if setup_tuist_cache and not full_handle:
            suggested_owner = tuist_owner or owner or "local"
            full_handle = text_or_prompt(
                "Tuist full handle",
                prefilled=prefilled.get("full_handle"),
                input_fn=input_fn,
                output_fn=output_fn,
                default=f"{suggested_owner}/{repo_name}",
                validator=validate_full_handle,
                non_interactive=non_interactive,
            )
        while setup_tuist_cache and full_handle and dependencies.full_handle_exists(full_handle) and not bound_existing_full_handle:
            output_fn(f"`{full_handle}` already exists in Tuist Cloud.")
            if non_interactive:
                raise ValueError(f"`{full_handle}` already exists in Tuist Cloud.")
            resolution = prompt_choice(
                cmp.build_full_handle_exists_resolution_question(full_handle),
                input_fn=input_fn,
                output_fn=output_fn,
            )
            if resolution == "bind-existing":
                bound_existing_full_handle = True
                break
            if resolution == "abort":
                output_fn("Aborted before writing files.")
                return 1
            suggested_owner = tuist_owner or owner or "local"
            full_handle = prompt_text(
                "Tuist full handle",
                input_fn=input_fn,
                output_fn=output_fn,
                default=f"{suggested_owner}/{repo_name}",
                validator=validate_full_handle,
                non_interactive=non_interactive,
            )

    create_initial_commit = choose_or_prompt(
        cmp.build_confirmation_question(
            "create_initial_commit",
            "Git",
            "Create the initial commit?",
        ),
        prefilled=prefilled.get("create_initial_commit"),
        input_fn=input_fn,
        output_fn=output_fn,
        non_interactive=non_interactive,
    ) == "yes"
    push_after_init = False
    if create_initial_commit and mode != "local-only":
        push_after_init = choose_or_prompt(
            cmp.build_confirmation_question(
                "push_after_init",
                "Git",
                "Push the initial commit after setup?",
            ),
            prefilled=prefilled.get("push_after_init"),
            input_fn=input_fn,
            output_fn=output_fn,
            non_interactive=non_interactive,
        ) == "yes"

    approvals = cmp.collect_approvals()
    approvals["create_github_repo"] = "confirmed" if mode != "local-only" else "declined"
    approvals["create_tuist_cloud_project"] = "confirmed" if create_tuist_cloud else "declined"
    approvals["setup_tuist_cache"] = "confirmed" if setup_tuist_cache else "declined"
    approvals["create_initial_commit"] = "confirmed" if create_initial_commit else "declined"
    approvals["push_after_init"] = "confirmed" if push_after_init else "declined"

    template_source_path, temp_template_dir = dependencies.clone_template(template)
    try:
        payload = dependencies.build_payload(
            mode=mode,
            template=template,
            template_source_path=str(template_source_path),
            destination_path=str(destination_path),
            destination_strategy=destination_strategy,
            project_name=project_name,
            bundle_id=bundle_id,
            ios_simulator_device=ios_simulator_device,
            approvals=approvals,
            owner=owner,
            repo_name=repo_name,
            full_handle=full_handle,
            visibility=visibility,
        )
        init_result = dependencies.run_initializer(payload)
        dependencies.execute_side_effects(
            payload=payload,
            approvals=approvals,
            destination_path=destination_path,
        )
    finally:
        if temp_template_dir is not None:
            temp_template_dir.cleanup()

    output_fn("Project created.")
    output_fn(f"Path: {init_result['destination_path']}")
    output_fn("Suggested next commands:")
    output_fn("  mise trust mise.toml")
    output_fn("  mise run warm-external-cache")
    output_fn("  mise run build-ios-sim")
    output_fn("  mise run test-ios")
    return 0
