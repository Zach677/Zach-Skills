---
name: zach-absorb-reference
description: >
  Use when a project wants to absorb an admired reference project's
  architecture ("吸收 X 的精华", "参照 X 的思想", "学 X 的架构"), or when a
  project that previously copied a reference has drifted into dead
  scaffolding and needs rework ("之前吸收过但需要重构"). Converts reference
  patterns into trigger-based rules in the target's agent docs instead of
  pre-created types, and audits prior absorption for zero-consumer artifacts.
metadata:
  author: zach
  version: "1.0.0"
---

# Absorb a Reference Project Without Cargo-Culting It

Use this skill when Zach points at a reference project he admires and asks a target project to absorb its strengths, or asks to clean up a target that already tried. The failure mode this skill prevents: copying the reference's *artifacts* (types, files, folder stubs) instead of its *rules*. Artifacts without consumers rot into dead code; rules fire exactly when a real need arrives.

## When to use

- Zach names a reference repo and a target repo and asks to absorb, imitate, or learn from the reference.
- A target project contains reference-shaped types with no production consumers (prior absorption gone stale).
- Not for: generic code review with no reference involved, writing the reference project itself, or copying product/UX decisions (those are per-product calls, not absorption).

## Scope

- Stack-agnostic: the method came from a UIKit/SwiftPM case but applies to any codebase with agent docs (`AGENTS.md` / `CLAUDE.md`).
- Prerequisites: read access to both repos; the target has (or will get) an agent rules file; the target has runnable verification gates (tests, build, linters).

## Inputs

| Variable | Meaning |
|---|---|
| `TARGET_REPO` | Absolute path of the project absorbing or being reworked |
| `REFERENCE_REPO` | Absolute path of the admired reference project |
| `MODE` | `absorb` (fresh) or `rework` (previously absorbed, now drifted). If unstated, detect: reference-shaped types with zero production consumers in the target means `rework` |

## Workflow

```text
[1] Snapshot both repos
      -> git status of target (do not touch user WIP)
      -> map reference structure; read its AGENTS/CLAUDE rules sections

[2] Verify every candidate pattern IN THE REFERENCE
      -> consumer count: grep who actually uses the type/pattern there
      -> rule backing: does a written rule enforce it there?
      -> a pattern earns absorption only with real consumers + ideally a rule

[3a] MODE=absorb: write trigger-based rules into target agent docs
      -> "when the first X arrives, create Y shaped like Z" + concrete shape
      -> copy tooling that carries its own consumers (Makefile gates, validators)
      -> never pre-create app types, folders, or DI slots for future needs

[3b] MODE=rework: zero-consumer audit of previously copied artifacts
      -> grep production consumers for every reference-shaped type
      -> classify: rule-carried (usually alive, keep) vs artifact-carried (husk)
      -> delete husks + the tests that pin them + orphaned resources
      -> re-express what the husk was *for* as a trigger-based rule (3a)

[4] Sync docs in the same change
      -> agent docs stop describing the template era; growth meta-rules added
      -> product docs (PRD/README) match shipped reality

[5] Verify
      -> full test suite + build + catalog/lint gates, output read not just exit code
      -> grep evidence recorded for every deletion
```

### [1] Snapshot

Run `git status --short --branch -uall` in the target first; modified or untracked files are Zach's work in progress, never stash or revert them. Then map the reference: top-level layout, its rules file, its Makefile and scripts. The reference's own rules sections are the highest-value reading, because they show which disciplines the reference considers load-bearing.

### [2] Verify in the reference

Judge each candidate pattern by evidence inside the reference itself, not by how good it looks:

```bash
grep -rln "TypeName" "$REFERENCE_REPO" --include="*.swift" | wc -l   # consumer count
grep -n "TypeName" "$REFERENCE_REPO/AGENTS.md"                        # rule backing
```

A preferences type with dozens of consumers and a rules section enforcing access through it is a real strength. The same type copied into a project with zero consumers is decoration. The strength was never the type; it was consumers plus rule.

### [3a] Absorb as rules

Each absorbed pattern becomes a rule in the target's agent docs with three parts: the trigger ("when the first user setting ships"), the shape ("typed static accessors over UserDefaults, reverse-DNS keys, a default and a test per key"), and the prohibition ("do not create the type before the trigger"). Add two meta-rules so absorption stays rule-shaped after this session:

- Adopt reference patterns as rules in this file, not as pre-created types; a new type must ship with at least one production consumer in the same change.
- When a feature area accumulates its second nontrivial convention, capture it as a rules section in the same change.

Rules must be self-contained: describe the shape inline, never link the reference repo's machine path, and never import the reference's dependencies just to mirror its implementation.

### [3b] Rework audit

For every type or file that traces to the reference: count production consumers (tests excluded), check who constructs it, check what would break. Husks show a consistent signature: only tests reference them, or only each other. Delete the husk, the pinning test, and orphaned side-resources (localization keys, assets, doc mentions). Forwarding aliases left by past renames are the same disease: production calls the new name, tests call the old one; update tests to the real API and delete the aliases.

### [4] Doc sync

Stale docs are the largest source of "this project feels messy": an agent file still describing the project as a starter template misleads every future agent run. Rewrite the shape sections to present reality, and update product docs whose claims the implementation has overtaken (schema described but never built, flows that navigate differently, single-X wording after multi-X shipped).

### [5] Verify

Run the target's full gates and read the output. After "observably equivalent" refactors, trust only the suite: whole-record equality assertions catch precision and round-trip subtleties that reasoning misses.

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| Copying the reference's types/files as "preparation" | Copy rules with triggers; types are created the day the trigger fires, with a consumer |
| Judging a pattern by how the reference looks | Verify in the reference: consumer count + rule backing; no consumers there means it is decoration there too |
| Calling a type alive because tests use it | Test-only consumers pin dead code; update the test to the real API, then delete both |
| Deleting on a "zero callers" claim without evidence | Repo-wide grep including tests, resources, string catalogs, docs, dynamic lookups; record the grep |
| Leaving rename forwarding aliases "for compatibility" | Production already calls the new name; migrate tests, delete aliases in the same change |
| Forgetting side-resources of deleted UI | Sweep localization keys, assets, and doc references orphaned by the deletion; run catalog validators |
| Agent docs still describing the template era | Rewrite shape/placement sections to present reality in the same change as the deletions |
| Hardcoding the reference repo's local path into target docs | Rules are self-contained; machine paths drift and leak usernames |
| Skipping the suite because the refactor "is equivalent" | Run everything; equality tests catch round-trip subtleties reasoning misses |
| Verification gaps discovered but left as-is | If the test plan misses a package or gate, fix the plan in this session and rerun |

## Rules

- A pattern earns absorption only with real production consumers in the reference, ideally backed by a written rule there.
- New types ship with at least one production consumer in the same change, or they do not ship.
- Tooling that carries its own consumers (build gates, validators, scripts wired into the Makefile) may be copied directly.
- Every deletion carries grep evidence; every batch ends with the full verification gates green.
- Doc sync happens in the same change as the code it describes.
- Do not commit or push the target repo without Zach's go-ahead.

## Verification

- [ ] Target worktree contains no clobbered user WIP (`git status` before and after).
- [ ] Each absorbed pattern cites its in-reference evidence (consumer count or rule line).
- [ ] Each deletion cites grep evidence covering code, tests, resources, and docs.
- [ ] Target agent docs contain the trigger-based rules and the two growth meta-rules.
- [ ] Full test/build/lint gates ran in this session with output read, not just exit codes.
- [ ] Product docs match shipped behavior (no template-era or overtaken claims left).
