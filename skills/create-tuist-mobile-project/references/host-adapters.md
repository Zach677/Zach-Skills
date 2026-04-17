# Host Adapters

`create-tuist-mobile-project` now has one shared interview core and three intended frontends:

1. **Terminal**
   - entrypoint: `ztm`
   - implementation: `bin/zach-mobile-wizard`
   - interaction: one-question-at-a-time text prompts in the terminal

2. **Codex**
   - shared source: `scripts/create_mobile_project.py`
   - adapter entrypoint: `build_codex_interaction_question(...)`
   - runtime requirement for clickable UI: host must support `request_user_input`

3. **Claude Code**
   - shared source: `scripts/create_mobile_project.py`
   - adapter entrypoint: `build_claude_interaction_prompt(...)`
   - runtime requirement for clickable or structured prompting: host must support `AskUserQuestion`

## Shared Rule

The core interview logic must live in the helper module, not in three separate host-specific prompt scripts.

That means:

- the question order comes from `next_interview_question(...)`
- choice effects come from `apply_choice_answer(...)`
- text effects come from `apply_text_answer(...)`
- payload and side effects still route through `build_payload(...)` and `execute_side_effects(...)`

The hosts are only renderers.

## Codex

### Clickable path

Use `build_codex_interaction_question(...)` when:

- the next question is a choice question
- every option is available
- the runtime supports `request_user_input`

That is the safe path for clickable selections.

### Fallback path

If the next question is:

- a text question, or
- a choice question with blocked options, or
- the runtime is not in a mode that supports `request_user_input`

then Codex should not fake clickable UI. It should either:

- ask the one question in plain text, or
- delegate to `ztm`

## Claude Code

Use `build_claude_interaction_prompt(...)` for the next question in the shared state machine.

If Claude runtime supports `AskUserQuestion`, the host can wrap that prompt into a structured question call.

If not, it can still render the prompt as plain text and keep the one-question-at-a-time flow.

## Triggering Guidance

### Best user-facing trigger

For local terminal work, the intended trigger is:

```bash
ztm
```

This is the shortest supported user command.

### Skill trigger

For AI-driven project creation, the intended skill trigger remains:

```text
create-tuist-mobile-project
```

The host should then decide whether to:

- render the next question as clickable
- render the next question as plain text
- or delegate the whole flow to `ztm`

## Runtime Matrix

| Host | Clickable support | Expected path |
|---|---|---|
| Codex Plan mode | yes, when question is fully renderable | `build_codex_interaction_question(...)` |
| Codex Default mode | no | plain text one-question fallback or `ztm` |
| Claude Code with AskUserQuestion support | host-dependent | `build_claude_interaction_prompt(...)` |
| Terminal | no clickable UI | `ztm` |

## Product Boundary

This repo now owns:

- the interview schema
- the interview state machine
- the terminal fallback
- the adapter contracts

This repo does **not** own:

- Codex host mode switching
- Codex desktop chat rendering
- Claude Code host UI rendering

Those last-mile integrations belong to the hosts themselves.
