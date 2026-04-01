# Config Schema

This task-level schema covers the parser, candidate-discovery, and plan-mode fields that exist so far.

## Top-Level Keys

- `scan_roots`
  - List of absolute or relative paths to scan for Tuist candidates.
  - Relative paths are resolved from the directory that contains `EXTEND.md`.
- `include_repos`
  - Optional allow-list of repo names to keep in scope.
- `exclude_repos`
  - Optional block-list of repo names to skip.
- `allow_push`
  - Boolean toggle for whether later tasks may push branches.
- `allow_pr`
  - Boolean toggle for whether later tasks may open pull requests.

## Repo Table

Each repo entry lives under `[repos.<name>]`.

- `path`
  - Filesystem path to the repo root.
  - Relative paths are resolved from the directory that contains `EXTEND.md`.
- `verify_commands`
  - Ordered list of verification commands for that repo.
- `base_branch`
  - Optional base branch override.

## Planning Notes

The current planning layer derives these statuses from the config plus each repo's `mise.toml`:

- `up-to-date`
- `needs-upgrade`
- `skipped-missing-verification`
- `skipped-config-error`

When `verify_commands` is empty, the planner stays report-only and suggests one fallback command:

- `mise run test-macos` when `mise.toml` mentions `test-macos`
- `mise run run-macos` when `mise.toml` mentions `run-macos`
- `mise exec -- tuist generate --no-open` otherwise
