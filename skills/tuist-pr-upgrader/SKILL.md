---
name: tuist-pr-upgrader
description: Use when scanning multiple Tuist repos, upgrading their pinned Tuist version, and opening one PR per repo.
---

# Tuist PR Upgrader

Tuist PR Upgrader is the shell for a skill that will scan Tuist projects, update the pinned Tuist version in `mise.toml`, and keep one upgrade PR per repo.

## Trigger Cases

- The user wants to bump Tuist across several repositories and expects one PR per repo.
- A report highlights mixed Tuist versions or a stale `tuist` binary that must be reconciled.
- Automation must respect user preferences for scanning roots, repo filters, and whether pushes/PRs are allowed.

## Workflow

1. Read `EXTEND.md` before acting; without it, stay in report-only mode.
2. Use the configured scan roots and repo filters to identify which Tuist repos belong in the workflow.
3. Keep the skill contract centered on one repo at a time, one branch at a time, and one PR at a time.
4. Load references on demand as the scan / plan / run implementation lands under `scripts/`.

## Guardrails

- Always read `EXTEND.md` before acting; without it, stay in report-only mode and do not change repos.
- Only interact with repos explicitly enabled by `scan_roots`, `include_repos`, and `exclude_repos` in `EXTEND.md`.
- Treat push and PR creation as opt-in behavior controlled by config.
- Keep runtime behavior narrow: pinned Tuist version changes, repo-local verification, and one PR per repo.
- Load only the references and scripts needed for the current step.

## Files To Load On Demand

- [references/README.md](references/README.md)
