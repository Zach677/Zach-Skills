# Config Schema

This task-level schema covers only the parser and candidate-discovery fields.

## Top-Level Keys

- `scan_roots`
  - List of absolute or relative paths to scan for Tuist candidates.
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
- `verify_commands`
  - Ordered list of verification commands for that repo.
- `base_branch`
  - Optional base branch override.
