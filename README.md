# Zach Skills

This repo is now a multi-skill workspace, not a single-skill product repo.

Each skill owns its own directory under `skills/`, along with its own:

- `SKILL.md` trigger and workflow doc
- `README.md` human setup and runbook
- `references/` long-form docs
- `scripts/` local helpers
- `agents/` optional agent metadata
- `EXTEND.example.md` for non-secret user preferences when needed

## Layout

```text
.
├── README.md
├── LICENSE
├── skills/
│   ├── tuist-pr-upgrader/
│   └── wechat-hot-writer/
└── tests/
```

## Current Skills

| Skill | Purpose | Docs |
|---|---|---|
| `wechat-hot-writer` | WeChat topic discovery, article packaging, visual prep, draft staging, and history sync | [skills/wechat-hot-writer/README.md](skills/wechat-hot-writer/README.md) |
| `tuist-pr-upgrader` | Scan Tuist repos, bump `.tuist-version`, and open PRs per repo | [skills/tuist-pr-upgrader/README.md](skills/tuist-pr-upgrader/README.md) |

## Repo Conventions

- Put new skills under `skills/<skill-name>/`.
- Keep root docs repo-level only. Do not turn the root `README.md` into a single skill manual again.
- Put non-secret, user-editable preferences in `EXTEND.md`.
- Put secrets in `.env`.
- Keep runtime output local to the skill directory and out of git.
- Add or update tests in `tests/` when a skill's behavior changes.

## Adding a New Skill

Use the scaffold script:

```bash
python3 scripts/new_skill.py "My New Skill" \
  --description "Use when this skill should trigger for a reusable workflow." \
  --with-extend \
  --with-agent
```

That creates `skills/my-new-skill/` with:

- `SKILL.md`
- `README.md`
- `references/README.md`
- `scripts/README.md`
- optional `EXTEND.example.md`
- optional `agents/openai.yaml`

Then finish the real work:

1. Replace the placeholder workflow in the generated `SKILL.md`.
2. Rewrite the generated `README.md` into a real runbook.
3. Remove optional files you don't actually need.
4. Add or update tests under `tests/`.
5. Update the root skill index if the new skill should be listed.
6. Run verification before you call it done.

## Verification

```bash
python3 -m unittest discover -s tests -q
```
