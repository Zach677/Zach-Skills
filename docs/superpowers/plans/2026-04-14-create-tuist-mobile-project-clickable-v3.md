# Create Tuist Mobile Project Clickable v3 Plan

**Goal:** Prepare `create-tuist-mobile-project` for true clickable interview questions by moving branch-question semantics into tested code and documenting the runtime adapter strategy.

## Scope

- add structured branch-question builders to `skills/create-tuist-mobile-project/scripts/create_mobile_project.py`
- add unit coverage for the new question schema and request-user-input mapping rules
- add a design spec that explains the host-runtime constraint and the fallback model

## Tasks

### Task 1: Add structured question builders

**Files**

- Modify: `skills/create-tuist-mobile-project/scripts/create_mobile_project.py`

**Work**

- add a typed question schema for branch questions
- add builders for:
  - mode
  - template
  - visibility
  - destination strategy
- add a mapping helper for the runtime-native clickable question payload
- reject mappings that would silently drop blocked options

**Done when**

- the helper module can produce a structured branch question without relying on prompt text alone

### Task 2: Add tests for the question schema

**Files**

- Modify: `tests/test_create_mobile_project.py`

**Work**

- verify mode questions preserve all modes and mark blocked choices
- verify template and destination-strategy questions map cleanly to clickable payloads
- verify blocked questions are refused by the clickable mapper

**Done when**

- the new question behavior is covered by unit tests

### Task 3: Add the v3 design docs

**Files**

- Create: `docs/superpowers/specs/2026-04-14-create-tuist-mobile-project-clickable-design.md`
- Create: `docs/superpowers/plans/2026-04-14-create-tuist-mobile-project-clickable-v3.md`

**Work**

- explain why `SKILL.md` alone cannot create clickable UI
- explain the two-path runtime model:
  - clickable UI when supported
  - single-step text fallback otherwise
- define the acceptance criteria for the next real integration step

**Done when**

- a future worker can implement the runtime hook without rediscovering the product rules

## Verification

Run:

```bash
python3 -m unittest tests.test_create_mobile_project -q
python3 -m unittest discover -q
```

## Output

Open a draft PR from this branch so the next step can focus only on host-runtime integration instead of rediscovering the schema and adapter design.
