---
name: create-tuist-mobile-project
description: Use when creating a new Tuist iOS or iOS plus Catalyst project from a public template with interactive setup.
---

# Create Tuist Mobile Project

This skill is the evolving orchestration layer for the project-creation flow above `bin/zach-mobile-init`. The helper module now implements capability detection, blocker reporting, approval collection, payload assembly, and side-effect sequencing; later tasks will wire the interactive interview onto those helpers instead of re-implementing them.

## Trigger Cases

- requests to boot a new Tuist iOS or iOS+Catalyst project from a public template.
- requests to scaffold a fresh local-only, GitHub-backed, or Tuist-Cloud-backed Tuist mobile project from the public starter templates.

## Workflow

1. Detect the local capabilities: `git`, `gh`, `gh auth status`, `mise`, `mise exec -- tuist version`, and `mise exec -- tuist auth whoami`. The helper in `scripts/create_mobile_project.py` now exposes `detect_capabilities(repo_root=...)` plus `describe_mode_blockers()` so the skill presents which modes are blocked (missing or unauthenticated) without silently downgrading any choice.
2. Ask for the creation mode and template shape (`local-only`, `github-backed`, `github-and-tuist-cloud`, then choose pure iOS or iOS + Catalyst). Keep all three modes explicit choices, and clarify blocked modes before proceeding instead of filtering them out.
3. Collect project metadata in the interview order required by the spec: project name; destination path; GitHub owner only when the selected mode includes GitHub; repo name, where any default derived from the project name must still be explicitly confirmed by the user; repo visibility only when the selected mode includes GitHub; bundle identifier; default iOS simulator device; then, when the selected mode is `github-and-tuist-cloud` and the capability state supports it, ask separately whether to create the Tuist Cloud project and whether to run `tuist setup cache`; finally ask about initial commit and push choices. The JSON handoff uses `full_handle`, which is derived from the confirmed owner/repo by default and should only surface as an optional override when needed.
4. Fail closed on setup conflicts before execution: if the target directory already exists, ask the user to choose `reuse`, `replace`, or `abort`; if the requested GitHub repo name is already taken, ask whether they want to choose another repo name and, if not, force an explicit follow-up choice to switch modes or abort; if the requested `full_handle` already exists, ask whether they want to bind to the existing handle or choose another handle.
5. When the selected mode is `github-and-tuist-cloud` and the capability state supports it, ask separate confirmations for Tuist Cloud project creation and `tuist setup cache`. Confirm every external side effect before execution (GitHub repo creation with the chosen visibility, Tuist Cloud creation, `tuist setup cache`, initial commit, push) by using `collect_approvals()` as the approval shape and then replacing `not_asked` with explicit answers during the interview. Never downgrade silently when a capability is missing; `ensure_mode_capabilities()` raises first so the conversation must redirect or fix tooling.
6. When the mode is `github-backed` or `github-and-tuist-cloud`, call `gh repo create` only after explicit approval.
7. Resolve the destination path and prepare a local template source path. In later tasks, run `bin/zach-mobile-init --config <path-to-json-config>` from the Zach-Skills repo root with the filled-in metadata and template choice. The future CLI consumes that prepared local source and performs local file mutation only.
8. If Tuist Cloud creation is confirmed, later tasks will run `mise exec -- tuist project create <full_handle>` from the chosen project root. If cache setup is confirmed, later tasks will run `mise exec -- tuist setup cache --path <destination_path>` afterward.
9. Treat `mise run warm-external-cache` as the default post-init local verification/setup step once the initializer and templates exist. Run it from the generated project `destination_path`, then commit/push if requested.
10. Present the final destination path, repo URL, and a quick checklist of the available commands.

## Capability Detection Targets

| Capability | Purpose |
|---|---|
| `git` | Local source required for every mode. |
| `gh` | Needed for GitHub-backed creation. |
| `gh auth status` | Required before creating repos or pushing. |
| `mise` | Used for cache warming and the local workflow. |
| `tuist` | Needed for template generation. |
| `tuist auth whoami` | Required to enable Tuist Cloud features. |

Summaries must surface which capabilities are missing so the user can fix them instead of the skill guessing.

## Confirmation Guardrails

- Every action that reaches beyond the local filesystem (repo creation with the chosen visibility, Cloud project creation, cache setup, pushes) needs a yes/no confirmation.
- If a capability is missing for the requested mode, stop, explain why the mode is blocked, and ask whether to switch or fix the dependency before continuing.
- If the destination directory already exists, stop and require an explicit `reuse`, `replace`, or `abort` choice before continuing.
- If the requested GitHub repo name is unavailable, stop and ask the user whether they want to choose another repo name.
- If the requested `full_handle` already exists, stop and ask whether the user wants to bind to the existing handle or choose another handle.
- The skill never silently switches from GitHub to local-only or from Tuist Cloud to cache-less behavior.

## CLI Handoff

Once the interview is complete, this skill is expected to build one in-memory payload describing the selected mode, template, `template_source_path`, `destination_path`, `destination_strategy`, names, identifiers, handle, device, cache slug, and the final approved execution booleans (`create_initial_commit`, `push_after_init`, `setup_tuist_cloud`, `setup_tuist_cache`). Later tasks will serialize that payload to a temporary JSON file and, from the Zach-Skills repo root, pass its path to `bin/zach-mobile-init --config <path-to-json-config>`, which will consume the prepared local template source and be the only tool that mutates the starter files.

## Guardrail References

- See [references/flow.md](references/flow.md) for the detailed flow diagram and decision points.
- `scripts/create_mobile_project.py` is the current helper surface for capability checks, blocker reporting, approvals, and payload assembly.

## Skill Helpers

- `detect_capabilities(repo_root=...)` probes the six required commands from an explicit working directory and records `available`, `unauthenticated`, or `missing` for each so the interview knows the true capability surface.
- `describe_mode_blockers()` maps the requirement tree (`local-only`, `github-backed`, `github-and-tuist-cloud`) to the exact missing capabilities so the user can decide whether to fix a toolchain rather than silently switching modes.
- `describe_mode_messages()` turns those blocker lists into user-facing mode summaries so the conversation can explain why a mode is blocked.
- `ensure_mode_capabilities()` raises when the requested mode lacks a capability, enforcing the no-silent-downgrade guardrail before any side effect occurs.
- `collect_approvals()` returns the fixed approval shape with `not_asked` defaults so the interview layer can replace them with explicit user answers.
- `build_payload()` assembles the in-memory contract (including mode-aware Cloud/cache booleans) that later tasks will serialize into the JSON config for `bin/zach-mobile-init`.

The skill continues to orchestrate the interview; after every confirmation is gathered it resolves the destination path, prepares the template source, and feeds the JSON payload to `bin/zach-mobile-init --config <path-to-json-config>` from the Zach-Skills repo root.

## Files To Load On Demand

- [references/flow.md](references/flow.md)
- [scripts/create_mobile_project.py](scripts/create_mobile_project.py)
