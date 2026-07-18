---
name: zach-codex-retrospective
description: >
  Use when Zach asks Codex to review recent Codex sessions, repo work, or
  collaboration friction and propose minimal, evidence-backed updates to
  AGENTS.md or Zach-owned skills. Also use for scheduled proposal-only
  maintenance of Zach's skills repository.
metadata:
  author: zach
  version: "0.1.0"
---

# zach-codex-retrospective

Use this skill to turn repeated Codex collaboration friction into small,
maintainable improvements to Zach's agent instructions and skills.

## Scope

- Review a time window, project, or cluster of recent Codex sessions.
- Identify repeated failures, user corrections, and successful defaults worth
  encoding.
- Propose minimal updates to `AGENTS.md` and 0-2 tiny skills.
- Default to proposal-only output. Do not edit files unless Zach explicitly asks
  to apply the proposals.

This skill is not for broad rewrites, generic productivity advice, or creating
large workflow frameworks from weak evidence.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `TIME_WINDOW` | Last 14 days | Session or repo history to review |
| `FOCUS` | None | Optional project, workflow, or pain point |
| `TARGET_REPO` | Current repo | Repo whose `AGENTS.md` and skills may be affected |
| `APPLY_MODE` | `proposal-only` | Use `apply` only when Zach explicitly asks |

## Workflow

```text
[1] Frame scope
      -> confirm or infer the time window, focus, repo, and apply mode

[2] Gather evidence
      -> inspect current AGENTS.md, README, relevant skills, recent git history,
         and available session context without inventing missing history

[3] Find patterns
      -> separate repeated friction, repeated success, and one-off noise

[4] Apply gates
      -> use references/change-gates.md before proposing AGENTS.md or skill changes

[5] Output proposal
      -> use references/retrospective-output-template.md exactly

[6] Apply only if requested
      -> make narrow edits, preserve existing voice, update symlinks/README when
         adding skills, then verify with git diff and repo checks
```

## Decision Rules

- Prefer a one-line `AGENTS.md` update over a new skill when the lesson is a
  general collaboration preference.
- Prefer a project-level `AGENTS.md` update when the lesson is tied to one repo's
  architecture, commands, release process, or data model.
- Extract a tiny skill only when the procedure is reusable, non-obvious, and
  would have saved meaningful time in at least two sessions or one high-cost
  failure.
- If evidence is weak, say so and propose no changes.
- Scheduled automation must stay proposal-only and should optimize for low
  noise over completeness.

## Output

For retrospective output, read and follow:

- `references/retrospective-output-template.md`
- `references/change-gates.md`

## Verification

When applying changes in a skills repo:

- Run `git diff --check`.
- Run `.githooks/pre-commit` if present.
- Confirm every new skill has a README entry and flat symlinks under both
  `.agents/skills/` and `.claude/skills/` when the repo uses that convention.
