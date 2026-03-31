---
name: tuist-pr-upgrader
description: Use when scanning multiple Tuist repos, upgrading their pinned Tuist version, and opening one PR per repo.
---

# Tuist PR Upgrader

Tuist PR Upgrader coordinates Tuist projects by updating the relevant `mise.toml` pins (including Tuist) and opening one PR per repo when permitted.

## Trigger Cases

- The user wants to bump Tuist across several repositories and expects one PR per repo.
- A report highlights mixed Tuist versions or a stale `tuist` binary that must be reconciled.
- Automation must respect user preferences for scanning roots, repo filters, and whether pushes/PRs are allowed.

## Workflow

1. Read `EXTEND.md` (scan roots, include/exclude lists, `allow_push`, `allow_pr`, and verification commands) before touching any repo.
2. For each repository under `scan_roots`, confirm it is a Tuist workspace, inspect its `mise.toml` pin, and determine the target Tuist release from the configuration.
3. Update `mise.toml` to the agreed pin, rerun manifests via the documented verification commands, and stage the changes per repo.
4. If `allow_push`/`allow_pr` are `true`, push and open a single PR per repo; otherwise gather the diffs into a report without touching remotes.
5. Summarize every repo’s outcome, highlight blockers, and note the verification commands that ran.

## Guardrails

- Always read `EXTEND.md` before acting; without it, stay in report-only mode and do not change repos.
- Only interact with repos explicitly enabled by `scan_roots`, `include_repos`, and `exclude_repos` in `EXTEND.md`.
- Push and open one PR per repo only when `allow_push` and `allow_pr` are `true`; otherwise keep the diffs local and report them.
- Run the documented verification commands exactly as listed in `EXTEND.md`; do not invent additional verification steps.
- Execute upgrades from each repository’s root so `mise run` and Tuist commands resolve without crossing contexts.

## Files To Load On Demand

- [references/README.md](references/README.md)
