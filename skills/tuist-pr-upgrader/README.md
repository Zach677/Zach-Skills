# Tuist PR Upgrader

`tuist-pr-upgrader` scans a batch of Tuist-backed repos, bumps their pinned Tuist dependency, and orchestrates one bilateral PR per repo when allowed.

## Setup

- Confirm the Python runtime used by `scripts/` matches the workspace policy (usually the default system Python).
- Copy `EXTEND.example.md` to an `EXTEND.md` under one of the suggested config paths and tailor `scan_roots`, `include_repos`, `exclude_repos`, and permission flags.
- Read `scripts/README.md` to understand what helpers exist before running the skill.

## Runbook

1. Load the repo set and permissions from `EXTEND.md`.
2. Trigger the upgrade automation described in `scripts/README.md` or the linked helpers.
3. Collect the summary: repos touched, Tuist bump diffs, and which results produced PRs versus drafts.
4. Report any repos skipped because they were outside the allowed set or because pushes/PRs were disabled.
