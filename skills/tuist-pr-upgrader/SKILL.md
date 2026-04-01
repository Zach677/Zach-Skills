---
name: tuist-pr-upgrader
description: Use when coordinating one-PR-per-repo Tuist upgrades across multiple repositories with config-gated automation.
---

# Tuist PR Upgrader

Tuist PR Upgrader scans configured Tuist projects, plans a one-PR-per-repo upgrade, and can execute the guarded workflow when config allows it.

## Preferences

Read `EXTEND.md` from the first path that exists:

1. `.zach-skills/tuist-pr-upgrader/EXTEND.md`
2. `${XDG_CONFIG_HOME:-$HOME/.config}/zach-skills/tuist-pr-upgrader/EXTEND.md`
3. `~/.zach-skills/tuist-pr-upgrader/EXTEND.md`

When no `EXTEND.md` exists, stay in report-only mode.

## Trigger Cases

- The user wants to bump Tuist across several repositories and expects one PR per repo.
- A report highlights mixed Tuist versions or a stale `tuist` binary that must be reconciled.
- Automation must respect user preferences for scanning roots, repo filters, and whether pushes/PRs are allowed.

## Workflow

1. Read `EXTEND.md` before acting; without it, stay in report-only mode.
2. Use the configured scan roots and repo filters to identify which Tuist repos belong in the workflow.
3. Run one of the script entry points from the repo root:
   - `python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py scan`
   - `python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py plan`
   - `python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py run --dry-run`
4. Keep the workflow centered on one repo at a time, one branch at a time, and one PR at a time.
5. Load references on demand when config keys or report semantics need clarification.

## Guardrails

- Always read `EXTEND.md` before acting; without it, stay in report-only mode and do not change repos.
- Only interact with repos explicitly enabled by `scan_roots`, `include_repos`, and `exclude_repos` in `EXTEND.md`.
- Treat push and PR creation as opt-in behavior controlled by config.
- Keep runtime behavior narrow: pinned Tuist version changes, repo-local verification, and one PR per repo.
- Use `--dry-run` when you want branch and PR intent without mutating repos.
- Load only the references and scripts needed for the current step.

## Files To Load On Demand

- [references/README.md](references/README.md)
- [references/config-schema.md](references/config-schema.md)
