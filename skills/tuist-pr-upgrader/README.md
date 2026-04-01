# Tuist PR Upgrader

Coordinate Tuist upgrades across multiple repositories with a config-gated `scan / plan / run` workflow. The script reads a fenced `toml` block from `EXTEND.md`, discovers Tuist candidates, plans a one-PR-per-repo upgrade, and can execute the guarded branch / verify / PR flow.

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
3. Make sure `mise`, `git`, and `gh` are installed and available on your shell path.

## Running the Skill

Run from the repo root:

```bash
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py scan
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py plan
python3 skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py run --dry-run
```

Use `--extend /absolute/path/to/EXTEND.md` to override the default lookup order.

Expected outcomes:

- `scan`
  - Prints the discovered Tuist candidate repos and the repos explicitly configured in `EXTEND.md`.
- `plan`
  - Prints the detected latest Tuist version, the scanned repos, and each repo's planner status.
- `run`
  - In `--dry-run`, reports which repos would branch or skip without mutating them.
  - Without `--dry-run`, performs the guarded repo workflow and respects `allow_push` / `allow_pr`.

## Preferences

Refer to `EXTEND.example.md` for the documented configuration keys and lookup order. Without `EXTEND.md`, this scaffold stays in report-only mode.

## Automation

Codex Automation should stay thin and call this skill on a schedule. Keep repo roots, repo filters, verification commands, and push/PR permissions in `EXTEND.md`, not in the automation prompt.
