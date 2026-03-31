---
name: tuist-pr-upgrader
description: Use when scanning multiple Tuist repos, upgrading their pinned Tuist version, and opening one PR per repo.
---

# Tuist PR Upgrader

Tuist PR Upgrader coordinates a batch of Tuist projects, updates their `.tuist-version`, and opens a PR per repo when approved.

## Trigger Cases

- The user wants to bump Tuist across several repositories and expects one PR per repo.
- A report highlights mixed Tuist versions or a stale `tuist` binary that must be reconciled.
- Automation must respect user preferences for scanning roots, repo filters, and whether pushes/PRs are allowed.

## Workflow

1. Read `EXTEND.md` (scan roots, include/exclude lists, `allow_push`, `allow_pr`) before touching any repo.
2. For each repository under `scan_roots`, confirm it is a Tuist project, note its `.tuist-version`, and determine the target version.
3. Apply the upgrade: update `.tuist-version`, regenerate manifests or run `tuist migrate` as needed, and stage the changes per repo.
4. If `allow_push`/`allow_pr` are `true`, push the branch and open the configured PR; otherwise capture the diff and describe next steps.
5. Summarize every repo’s outcome, surfaces blockers, and record the version we landed on.

## Guardrails

- Only interact with repos explicitly enabled by `scan_roots`, `include_repos`, and `exclude_repos` in `EXTEND.md`.
- Do not push or create PRs unless `allow_push` or `allow_pr` is `true`; otherwise only prepare local diffs/reports.
- Run upgrades from each repo’s root so Tuist regeneration commands resolve dependencies correctly.
- Log the target Tuist version, toolchain changes, and any required follow-up instructions in your summary.

## Files To Load On Demand

- [references/README.md](references/README.md)
