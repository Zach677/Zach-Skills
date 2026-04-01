# Tuist PR Upgrader

Minimal shell for coordinating Tuist upgrades across multiple repositories.

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

1. Copy [EXTEND.example.md](EXTEND.example.md) into one of the supported `EXTEND.md` paths.
2. Populate `scan_roots`, `include_repos`, `exclude_repos`, and the `allow_*` toggles to match your workflow.

## Running the Skill

This scaffold reserves `scripts/` for the CLI entry point and keeps the user-editable workflow configuration in `EXTEND.md`.

## Preferences

Refer to `EXTEND.example.md` for the documented configuration keys and lookup order. Without `EXTEND.md`, this scaffold stays in report-only mode.
