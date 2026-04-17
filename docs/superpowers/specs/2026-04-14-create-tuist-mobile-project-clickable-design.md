# Create Tuist Mobile Project Clickable Design

**Date:** 2026-04-14

## Goal

Upgrade `create-tuist-mobile-project` from a plain-text interview into a guided flow that can render clickable choices in the chat UI whenever the runtime supports it, while preserving the existing no-silent-downgrade guarantees.

## Current State

The current skill now asks one question at a time, but it still relies on plain-text replies. That solved the "comma-separated payload" problem, but it did not solve the UI problem:

- branch questions still look like text menus
- the user still has to type the answer manually
- the flow does not yet map onto a platform-native question primitive

The repo already contains the deterministic initializer (`bin/zach-mobile-init`) and the orchestration helper module (`skills/create-tuist-mobile-project/scripts/create_mobile_project.py`), so the missing piece is the interaction layer.

## Constraint

Clickable chat questions are not something `SKILL.md` can create by itself.

The runtime needs to support a question UI primitive such as `request_user_input`. That means the product has to support two execution paths:

1. **Interactive UI path**
   Uses the runtime question tool and renders clickable options in chat.

2. **Text fallback path**
   Uses the same question definitions, but presents them as single-step plain-text prompts when the runtime does not support the clickable UI.

The fallback must remain explicit and safe. It must not change the business rules.

## Design Principle

Question semantics should live in code, not only in prompt prose.

That means the helper module should expose structured question definitions that describe:

- the question identifier
- the title or header
- the prompt text
- the available options
- whether each option is available or blocked
- why an option is blocked

The renderer can then decide whether to:

- convert the question into a clickable UI payload
- or convert it into a single-turn plain-text prompt

## Interaction Model

### Question categories

**Clickable-first**

- creation mode
- template type
- GitHub visibility
- existing-directory strategy (`reuse`, `replace`, `abort`)
- yes/no confirmations for:
  - GitHub repo creation
  - Tuist Cloud project creation
  - `tuist setup cache`
  - initial commit
  - push

**Text-only**

- project name
- destination path
- GitHub owner
- GitHub repo name
- bundle identifier
- optional `full_handle` override

### Runtime rule

- If every option in a question is available, the runtime may render it as clickable.
- If a question contains blocked options, the runtime must not silently hide them.
- In that case, the runtime must either:
  - render a richer UI that supports disabled options, or
  - fall back to a plain-text question that shows all options and their blocked reasons.

This is why mode selection is slightly harder than template selection: mode selection may include blocked choices.

## Question Schema

The helper layer should expose a stable internal schema for branch questions.

Example shape:

```python
{
  "id": "mode",
  "header": "Mode",
  "prompt": "Choose the project creation mode.",
  "options": [
    {
      "value": "local-only",
      "label": "Local Only",
      "description": "Create the project locally only.",
      "availability": "available",
    },
    {
      "value": "github-backed",
      "label": "GitHub Backed",
      "description": "Create the local project and a GitHub repo.",
      "availability": "blocked",
      "blocked_reason": "gh auth status",
    },
  ],
}
```

This schema is richer than the runtime UI tool schema on purpose. It keeps the product logic lossless.

## Adapter Strategy

The runtime adapter layer should have two functions:

1. **Capability-aware question builder**
   Produces the internal question schema from current repo/tool state.

2. **UI mapper**
   Converts the internal schema into the runtime-native clickable payload only when that conversion is safe.

Safe means:

- every option is available, or
- the runtime eventually supports disabled options

Not safe means:

- blocked options would be hidden or flattened away

When conversion is not safe, the adapter must fall back to a plain-text prompt built from the same schema.

## Execution Mode Matrix

| Runtime | Clickable questions | Expected behavior |
|---|---|---|
| Plan mode with `request_user_input` | Yes | Use clickable UI for fully available branch questions |
| Default mode without `request_user_input` | No | Render the same questions as one-question plain text |
| Future widget/app flow | Yes | Can render richer states including disabled options and explanations |

## Concrete v3 Scope

v3 should deliver these pieces:

1. add structured question builders to `create_mobile_project.py`
2. add tests for:
   - mode question generation
   - template question generation
   - visibility question generation
   - destination strategy question generation
   - request-user-input mapping behavior
3. add a shared interview state machine with explicit answer-application helpers
4. add host adapter entrypoints for:
   - Codex
   - Claude Code
5. document that blocked options cannot be silently dropped
6. document that the future runtime integration should use clickable UI only when the question is representable without losing state

v3 does **not** need to ship the final runtime hook itself.

That final hook belongs in the host execution layer that actually has access to `request_user_input`.

## Acceptance Criteria

v3 is successful when:

- branch questions exist as structured code objects
- the next interview question can be derived from a shared state machine
- Codex and Claude Code adapter entrypoints exist in code
- tests lock their shape and blocked-option behavior
- the design explicitly describes when clickable rendering is allowed
- the design explicitly describes when fallback to plain text is required
- no business rule is duplicated only in prose

## Non-Goals

- faking clickable UI with markdown bullets
- hiding blocked modes from the user
- making `SKILL.md` pretend it can render UI by itself
- implementing a custom widget in this repo before the runtime integration path is chosen
