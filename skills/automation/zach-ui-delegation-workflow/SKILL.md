---
name: zach-ui-delegation-workflow
description: >
  Use when setting up or repairing a product repo where Codex owns logic and a
  separate UI agent owns presentation. Installs tracked delegation rules,
  handoff prompts, selector contracts, verification gates, and review reports.
metadata:
  author: zach
  version: "0.1.0"
---

# zach-ui-delegation-workflow

Set up a repo so UI implementation can be delegated without letting agents
blur product, data, and presentation ownership. The target state is a tracked
workflow: Codex implements or reviews non-UI logic, auto-creates a per-task UI
handoff when presentation work is needed, Zach directs the UI agent, and Codex
reviews the resulting diff against stable contracts.

## When to use

Use when:

- Zach wants Claude Code, Cursor, or another UI agent to own UI/UX changes while
  Codex owns logic, architecture, contracts, storage, API, sync, parser, or
  verification work.
- A project has design references but lacks durable agent boundaries.
- Codex keeps touching UI accidentally, or a UI agent keeps crossing into
  business logic.
- A repo needs a repeatable handoff/review loop rather than one-off chat prompts.

Do not use for:

- A single UI implementation task after the project already has a working
  delegation workflow.
- Pure visual critique or design exploration.
- Replacing product docs, ADRs, or roadmap discipline.
- Copying one repo's private rules into another repo unchanged.

## Inputs

- Current repo path and primary agent instruction file, such as `AGENTS.md`,
  `CLAUDE.md`, or project-specific rules.
- Existing design references, UI guidelines, test selectors, smoke tests, and
  dev commands.
- The desired ownership split between Codex and the UI agent.
- Any UI task that motivated the setup, if one exists.

## Files Provided

This skill is self-contained. It creates or updates files inside the target
project only. Use the target repo's existing docs layout when possible.

## Workflow

```text
[1] Inspect current project surfaces
[2] Define ownership boundaries
[3] Add tracked delegation docs
[4] Add automatic handoff rules
[5] Add UI completion and review loop
[6] Verify and explain daily usage
```

### [1] Inspect current project surfaces

Start read-only. Identify:

- Project instruction surfaces: `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`,
  docs standards, roadmap, and playbooks.
- UI surfaces: renderer directories, component files, CSS, static HTML, design
  system files, and visual references.
- Non-UI surfaces: data models, API types, persistence, auth, sync, parsing,
  search, workers, services, migrations, and test harnesses.
- Stable contracts: DOM IDs, smoke-test selectors, event names, state machines,
  user-visible status copy, request/response types, and verification commands.

Current project evidence wins over memory. If the repo has no durable docs, add
the smallest useful project-level rulebook first.

### [2] Define ownership boundaries

Write the boundary in repo terms:

- Codex owns product logic, architecture, data contracts, storage/search/import,
  auth/sync/parser work, and non-UI verification.
- Zach directs the UI agent directly for presentation implementation.
- The UI agent may edit only renderer presentation files: components, CSS,
  layout, typography, responsive behavior, and UI-only copy.
- The UI agent must not edit data contracts, storage, network protocols,
  parser/import/sync/auth logic, dependencies, roadmap/product scope, or fake
  connected states.

Adapt the categories to the repo. Do not import domain-specific nouns from the
source project unless they exist in the target repo.

### [3] Add tracked delegation docs

Prefer stable public project docs over ignored local overlays.

Create or update:

- Project agent rulebook: usually `AGENTS.md`.
- UI guideline document: visual constraints, information architecture, and
  project-specific design references.
- UI selector contract: stable IDs/classes/status copy and the protocol for
  changing them.
- UI verification playbook: dev command, desktop/mobile checks, contrast,
  hover/focus/disabled/loading states, smoke commands, and screenshot rules.
- UI handoff playbook: template, allowed/forbidden scope, open decisions,
  do-not-retry list, and acceptance checks.

Keep per-task prompts in a handoff directory, for example
`docs/handoffs/ui-agent/YYYY-MM-DD-<slug>.md`. New UI task, new prompt file.
Old handoffs are task snapshots, not permanent authority.

### [4] Add automatic handoff rules

The key rule is automatic, not user-triggered:

> When Codex changes, designs, or reviews non-UI logic and detects a concrete
> UI follow-up, Codex must create a self-contained UI handoff instead of editing
> presentation code. Zach does not need to ask for the handoff explicitly.

Allow Codex to skip only when:

- There is no UI consequence.
- The UI consequence is already fully covered by an existing unsent handoff.
- Zach explicitly asks Codex to implement UI in the current turn.

If there is no UI follow-up after non-trivial logic work, Codex should say so
briefly in the final answer.

### [5] Add UI completion and review loop

For medium or large UI tasks, ask the UI agent to write a short completion
report next to the handoff. It should include:

- Commit or diff base, if available.
- Files touched.
- Scope completed.
- Contracts preserved.
- Verification commands and layout checks.
- Known tradeoffs, blockers, or risks for Codex review.

Codex must treat the report as a claim, not proof. Review the actual diff,
selectors, non-UI boundaries, and command output.

### [6] Verify and explain daily usage

Run the repo's cheapest relevant gates:

- Markdown/whitespace: `git diff --check`.
- Docs links or formatting if the repo has a check.
- Existing typecheck/smoke checks only if touched docs reference commands that
  must be proven now.
- Git status in every repo touched.

Explain the usage contract:

- Run this skill once to bootstrap or repair the workflow.
- After setup, agents should follow project rules automatically.
- Daily UI tasks should use per-task handoff files, not re-run this skill.

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| Building a daily UI command instead of a project setup workflow | Make the project docs enforce the behavior after bootstrap. |
| Letting Codex write UI while "just helping" | Codex writes contracts and handoffs; UI implementation requires Zach's current-turn approval. |
| Hiding the rules in local ignored files | Put durable boundaries in tracked project docs. Local overlays are optional context only. |
| Copying private source-project paths | Scan the target repo and use its real files, commands, and contracts. |
| Treating handoff files as permanent docs | Extract durable lessons into rulebooks/playbooks; keep handoffs as task snapshots. |
| Trusting UI completion reports | Verify reports against the actual diff and command output. |
| Renaming selectors during visual polish | Preserve selector contracts unless Codex/Zach explicitly revises and verifies them. |

## Verification

- [ ] Target repo has tracked rules that name Codex ownership, UI-agent scope,
      forbidden non-UI surfaces, and Zach's role.
- [ ] Automatic UI handoff trigger is explicit and does not require Zach to ask.
- [ ] Per-task handoff path and completion-report path are documented.
- [ ] Selector contract and UI verification gates exist or are intentionally
      marked not applicable.
- [ ] No private source-project paths, secrets, raw transcripts, or one-off
      product constraints were copied into reusable guidance.
- [ ] `git diff --check` passes in every touched repo.
- [ ] Final answer names which repos were changed and whether anything is
      staged, committed, or left uncommitted.
