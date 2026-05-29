# Change Gates

Use these gates before proposing any retrospective change.

## AGENTS.md Updates

Accept only changes that are:

- Specific enough to change the next similar task.
- Supported by repeated evidence or one unusually expensive failure.
- Small enough to add little reading burden.
- Written in the voice and language of the target `AGENTS.md`.

Reject:

- Large rewrites or reorganizations.
- Vague rules such as "be careful" or "think harder".
- Long lists of prohibitions.
- Changes based on a single ordinary incident.

## Tiny Skill Extraction

Create or update a tiny skill only when all are true:

- The workflow appeared in at least two meaningfully different sessions, or one
  very high-cost incident.
- A standalone procedure would have saved Zach noticeable time or corrections.
- The trigger phrase is clear enough for Codex to use reliably.
- The first version can stay small and focused.
- The value is higher as a skill than as a short `AGENTS.md` rule.

Reject skills that duplicate existing guidance, encode temporary project trivia,
or mainly remind Codex to be more attentive.

## Global vs Project-Level Placement

- Global: cross-project collaboration style, planning defaults, review posture,
  preferred automation behavior, recurring user preferences.
- Project-level: repo-specific commands, architecture boundaries, data ownership,
  migration rules, release process, and local verification rituals.

When unsure, propose the narrower project-level change first.
