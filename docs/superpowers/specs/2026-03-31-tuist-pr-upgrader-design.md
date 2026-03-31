# Tuist PR Upgrader Design

**Date:** 2026-03-31

**Goal:** Create a reusable Codex skill that scans configured Tuist repositories, upgrades their pinned `mise` Tuist version one repo at a time, verifies each repo, and opens one PR per successful upgrade.

**Why this exists:** Tuist moves fast. Letting Homebrew silently drag multiple repos onto a new version is sloppy and hard to debug. The safer model is: pin per repo, then automate the upgrade workflow around that pin.

## Problem

The target workflow needs to handle several independent Tuist repos under one developer root without baking local-only details into the skill itself. The skill must stay open-source friendly while still supporting local automation for one user's machines and repositories.

The workflow also needs strong blast-radius control:

- one repo per branch
- one repo per PR
- no push or PR when verification fails
- no touching repos that lack explicit verification commands

## Users

- Primary: a solo developer with several Tuist repos under one parent directory
- Secondary: anyone else who wants the same workflow by supplying their own `EXTEND.md`

## Non-Goals

- Managing projects that do not use `mise.toml`
- Upgrading arbitrary dependencies beyond the pinned Tuist version
- Auto-guessing safe verification commands for unconfigured repos
- Bundling multiple repos into one branch or PR
- Requiring the skill body to contain local filesystem paths or private repo names

## Product Shape

Create a new skill in `Zach-Skills` named `tuist-pr-upgrader`.

The skill is a small orchestrator around a local script. The script handles scanning, planning, execution, and reporting. The skill documentation explains when to use it, which config file to provide, and which safety rules apply.

Codex Automation should call this skill on a weekly schedule. The automation stays thin. All durable behavior lives in the skill plus `EXTEND.md`.

## Core Decisions

### One repo, one branch, one PR

Each repo is processed independently. A failure in one repo must not block another from being upgraded.

### Configuration lives in `EXTEND.md`

The open-source skill cannot assume one user's local paths, repo names, base branches, or verification commands. Those values belong in `EXTEND.md`.

Without `EXTEND.md`, the skill must run in report-only mode.

### Missing verification means skip

If a repo does not define verification commands in `EXTEND.md`, the skill must skip that repo and include a suggested command in the final report. It must not attempt a best-guess upgrade.

### Existing same-version PR means skip

If the repo already has an open PR targeting the same Tuist version, the skill must skip it and report `existing PR found`.

## Candidate Repo Detection

The script scans configured roots and treats a directory as a Tuist candidate only when all of the following files exist:

- `Project.swift`
- `Tuist.swift`
- `mise.toml`

Detection is intentionally conservative. It prefers false negatives over touching the wrong repo.

## Configuration Model

The skill should read `EXTEND.md` before acting. The file should support a simple, human-editable structure that can express:

- `scan_roots`
- `include_repos`
- `exclude_repos`
- per-repo `path`
- per-repo `verify_commands`
- per-repo `base_branch` override
- `allow_push`
- `allow_pr`

The repo-specific section is the source of truth for execution. Even if scanning discovers other Tuist repos, only explicitly configured repos should be upgraded automatically.

An accompanying `EXTEND.example.md` should show a portable template without any local personal data.

## Workflow

### 1. Scan

The script scans configured roots and outputs:

- detected Tuist candidates
- configured repos that are valid for execution
- configured repos missing required fields
- unconfigured Tuist candidates that were found but will not be touched

### 2. Plan

The script fetches the latest stable Tuist version and compares it to each configured repo's pinned `mise.toml` version.

For each repo, it assigns one status:

- `up-to-date`
- `needs-upgrade`
- `skipped-dirty-worktree`
- `skipped-missing-verification`
- `skipped-existing-pr`
- `skipped-config-error`

### 3. Run

For each repo marked `needs-upgrade`, run this flow:

1. Verify git worktree is clean
2. Fetch remotes
3. Resolve the base branch
4. Check for an existing open PR for the same target version
5. Create a branch like `chore/tuist-4-171-2`
6. Update only the pinned `tuist = "x.y.z"` line in `mise.toml`
7. Run the repo's configured verification commands
8. If verification passes:
   - commit
   - push if allowed
   - create PR if allowed
9. If verification fails:
   - keep the local result for inspection
   - do not push
   - do not create a PR

## Git And PR Conventions

- Branch name: `chore/tuist-<version-with-dashes>`
- Commit message: `chore: bump Tuist to <version>`
- PR title: `chore: bump Tuist to <version>`

PR body should include:

- previous version
- new version
- verification commands run
- verification result summary

## Safety Rules

- No `EXTEND.md`: report only
- Dirty worktree: skip
- Missing verification commands: skip and suggest
- Verification failure: no push, no PR
- Existing same-version PR: skip
- Unsupported repo shape: skip

These rules matter more than throughput.

## Script Interface

Implement one local script at `skills/tuist-pr-upgrader/scripts/tuist_pr_upgrader.py`.

It should provide these commands:

- `scan`
- `plan`
- `run`

It should also support `--dry-run` so the whole workflow can be exercised without mutating remotes.

## File Layout

The skill should use this structure:

```text
skills/tuist-pr-upgrader/
├── SKILL.md
├── README.md
├── EXTEND.example.md
├── references/
│   └── config-schema.md
└── scripts/
    └── tuist_pr_upgrader.py
tests/
└── test_tuist_pr_upgrader.py
```

## Reporting

Each run should generate a concise report that includes:

- detected target version
- which repos were scanned
- which repos were upgraded
- which repos were skipped
- why each skip happened
- PR URLs for successful upgrades
- suggested verification commands for repos missing configuration

Markdown is the best default because Automation inbox items can render it cleanly.

## Testing Strategy

Unit tests should cover:

- candidate repo detection
- `EXTEND.md` parsing
- `mise.toml` version replacement
- skip conditions
- branch / commit / PR text generation

Tests should mock:

- latest-version lookup
- `git`
- `gh`
- subprocess command execution

Tests should not push to real remotes or create live PRs.

## Initial Real-World Targets

The current local developer root contains at least these obvious Tuist + `mise.toml` repos:

- `mitori`
- `Kigen`
- `SubPanda`

Those names are implementation examples for the author's local setup, not defaults that belong in the skill itself.

## Automation Shape

The weekly automation should:

1. run the skill
2. open an inbox item with the report

The automation should not embed repo-specific logic. That belongs in `EXTEND.md`.

## Risks

### Version lookup drift

The script needs a stable source for "latest stable Tuist version". If that source changes, the safe fallback is to fail closed and report the lookup issue.

### Verification command quality

The skill can only be as safe as the configured verification commands. That is why unconfigured repos must be skipped rather than guessed.

### GitHub auth

`gh pr create` depends on valid local auth. The script should detect auth failures and report them clearly.

## Recommended Next Step

After this spec is approved, write an implementation plan that:

- scaffolds the new skill in `Zach-Skills`
- defines the `EXTEND.md` schema more precisely
- implements scan / plan / run incrementally
- adds unit tests before the script logic is considered done
