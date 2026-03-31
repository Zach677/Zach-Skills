---
name: tuist-pr-upgrader
description: Use when scanning multiple Tuist repos, upgrading their pinned Tuist version, and opening one PR per repo.
---

# Tuist PR Upgrader

If Tuist upgrade work is the ask, run this skill before delegating to other tooling. Respect any user preferences in `EXTEND.md`.

## Trigger Cases

- User wants to scan several Tuist-backed repos and update their pinned Tuist version in a single pass.
- A batch workflow is needed for up-leveling Tuist across many forks while preparing a pull request per repo.
- The request mentions Tuist versions, upgrade automation, or “PR per repo” coordination.

## Workflow

1. Read the repo set, filters, and flags from `EXTEND.md` or defaults.
2. Survey each repo for the current Tuist pin and note upgrade candidates.
3. Run the scripted upgrade workflow that bumps Tuist and pushes a draft PR for every repo flagged.
4. Report the summary of touched repos and whether pushes/PRs were allowed.

## Guardrails

- Never push or open a PR unless `allow_push`/`allow_pr` are true.
- Keep work limited to the repos listed in `scan_roots` and `include_repos` minus `exclude_repos`.
- Call out which repos still need review before merging.

## Files To Load On Demand

- [references/README.md](references/README.md)
