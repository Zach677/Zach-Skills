# Tuist PR Upgrader

Minimal shell for coordinating Tuist upgrades across multiple repositories. The current script layer covers config loading, candidate discovery, and plan-mode version analysis; repo mutation and PR creation land later.

## Layout

```text
skills/tuist-pr-upgrader/
├── SKILL.md
├── README.md
├── EXTEND.example.md
├── references/
└── scripts/
```

## Setup

1. Copy the whole Markdown file [EXTEND.example.md](EXTEND.example.md) into one of the supported `EXTEND.md` paths.
2. Populate `scan_roots`, `include_repos`, `exclude_repos`, and the `allow_*` toggles to match your workflow.

## Running the Skill

This scaffold keeps the user-editable workflow configuration in `EXTEND.md` and reserves `scripts/` for the CLI entry point.

The current planning layer is responsible for:

- reading the pinned Tuist version from `mise.toml`
- comparing it to the latest stable Tuist release
- marking repos as `up-to-date`, `needs-upgrade`, `skipped-missing-verification`, or `skipped-config-error`
- suggesting fallback verification commands for report-only output when repo-specific commands are missing

## Preferences

Refer to `EXTEND.example.md` for the documented configuration keys and lookup order. Without `EXTEND.md`, this scaffold stays in report-only mode.
