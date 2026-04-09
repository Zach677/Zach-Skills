# Create Tuist Mobile Project

`create-tuist-mobile-project` is the evolving shell for a workflow that will orchestrate the interview, capability detection, and confirmation flow for creating a new Tuist-powered mobile project. The deterministic initializer now exists at `bin/zach-mobile-init`; the skill still defines the higher-level interview and orchestration contract around it.

## Responsibilities

- summarize CLI tooling (`git`, `gh`, `gh auth status`, `mise`, `mise exec -- tuist version`, `mise exec -- tuist auth whoami`) and surface missing capabilities.
- ask the user for the mode (`local-only`, `github-backed`, `github-and-tuist-cloud`) and template shape, then follow the spec interview order instead of freelancing question order.
- confirm every external side effect before executing it (repo creation with the chosen visibility, Tuist Cloud project creation, cache setup, initial commit, push).
- within `github-and-tuist-cloud`, ask separate confirmations for Tuist Cloud project creation and `tuist setup cache` instead of collapsing them into one toggle.
- fail closed when setup conflicts appear: an existing target directory requires an explicit `reuse`, `replace`, or `abort` choice; a taken GitHub repo name requires asking the user whether to choose another name and, if they refuse, forcing an explicit switch-mode-or-abort choice; and an existing `full_handle` requires asking whether to bind to it or choose another handle.
- run `gh repo create`, `mise exec -- tuist project create`, `mise exec -- tuist setup cache`, and Git actions only when the user has explicitly approved them once the orchestration layer is implemented.
- treat `mise run warm-external-cache` as the default local post-init setup/verification step, executed from the generated project `destination_path`.
- hand off the filled template, `template_source_path`, destination path, names, handle, identifiers, cache slug, and final approved booleans to `bin/zach-mobile-init --config <path-to-json-config>`, which will consume a prepared local template source and mutate the chosen starter.

## Default Interview Order

1. Ask for the creation mode.
2. Ask for the template selection.
3. Ask for the project name.
4. Ask for the destination path.
5. Ask for the GitHub owner only when the selected mode includes GitHub.
6. Ask for the repo name. The skill may derive a default from the project name, but the user must still confirm that repo name explicitly.
7. Ask for repo visibility only when the selected mode includes GitHub.
8. Ask for the bundle identifier.
9. Ask for the default iOS simulator device.
10. If the selected mode is `github-and-tuist-cloud` and current capabilities support it, ask separately whether to create the Tuist Cloud project and whether to run `tuist setup cache`.
11. Ask whether to create the initial commit and whether to push it.

`full_handle` is normally derived from the confirmed owner and repo name. It is not part of the default interview unless the user needs an explicit override.

`cache_service_slug` is normally derived from the confirmed `full_handle`. It belongs in the JSON handoff contract, not in the default interview unless the user needs an explicit override.

## Fail-Closed Branches

- If the target directory already exists, the skill must stop and ask the user to choose `reuse`, `replace`, or `abort`.
- If the requested GitHub repo name is already taken, the skill must stop and ask whether the user wants to choose another repo name; if not, it must force an explicit switch-mode-or-abort choice.
- If the requested `full_handle` already exists, the skill must stop and ask whether the user wants to bind to that handle or choose another one.

## Architecture

- Templates live in the planned public GitHub template repositories `github.com/Zach677/tuist-ios-starter` and `github.com/Zach677/tuist-ios-catalyst-starter`; the skill will later prepare a local copy of one of those templates as the CLI input source.
- `scripts/create_mobile_project.py` is the current shell helper surface for capability status reporting, approval collection, and payload construction.
- `references/flow.md` describes the intended decision tree, confirmations, and order of side effects that the remaining orchestration work must follow.

## Side-effect sequencing

The module now exposes `execute_side_effects`, which runs the confirmed operations in the required order: `gh repo create`, `mise exec -- tuist project create`, `mise exec -- tuist setup cache`, `mise run warm-external-cache`, and finally the git lifecycle (`init`, `add`, `commit`, and optional `push`). Each step is guarded by the collected approvals so the helpers never execute without an explicit “confirmed” answer, and they rely on the template metadata (`owner`, `repo_name`, `full_handle`, etc.) that the payload already assembled.

## References

- [Flow doc](references/flow.md)
- [Bootstrap shell stub](scripts/create_mobile_project.py)

## Agent Metadata

The agent metadata in `agents/openai.yaml` guides the default prompt so the skill triggers when a user needs a new Tuist mobile project setup.
