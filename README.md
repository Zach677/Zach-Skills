# Personal Zach Skills Repository

This repository stores personal Codex skills in a scalable directory layout.

## Layout

```text
Zach-Skills/
├── README.md
├── skills/
│   ├── automation/
│   │   └── zach-oss-governance-bootstrap/
│   │       ├── SKILL.md
│   │       ├── references/
│   │       ├── scripts/
│   │       └── templates/
│   └── publishing/
│       └── zach-wechat-daily-publisher/
│           ├── SKILL.md
│           ├── agents/
│           ├── references/
│           ├── scripts/
│           └── templates/
└── templates/
    ├── SKILL.template.md
    └── SKILL.with-references.template.md
```

## Conventions

- Place real skills only under `skills/`.
- Group skills by a stable domain such as `infrastructure`, `writing`, `research`, `automation`, or `content`.
- Each skill should live in its own directory and contain a single required `SKILL.md` file plus optional `agents/`, `references/`, `scripts/`, `templates/`, or `assets/` subdirectories.
- Keep the top-level `templates/` directory for reusable skill skeletons only. Files in that directory are not treated as active skills.
- Avoid storing credentials, tokens, or machine-specific secrets in skill files.
- Prefer one skill per directory, even when the first version is only a single `SKILL.md`.
- Use domain folders only as stable classification buckets; do not encode transient project names into the domain level.
- Use the `zach-` prefix for Zach-authored skills.

## Skills

| Skill | Purpose |
| ----- | ------- |
| [`zach-oss-governance-bootstrap`](skills/automation/zach-oss-governance-bootstrap/SKILL.md) | Bootstrap Ghostty-style open-source contribution governance for GitHub repos |
| [`zach-wechat-daily-publisher`](skills/publishing/zach-wechat-daily-publisher/SKILL.md) | AI-led daily WeChat article writing with cover generation, API draft publishing, and logs |

## Agent Integration

Skills are loaded by Codex-compatible agents (`.agent/`) and Claude Code (`.claude/`) via **flat symlinks** directly under their respective `skills/` directories. Each agent expects skills at exactly one level deep: `.agent/skills/<skill-name>/SKILL.md` or `.claude/skills/<skill-name>/SKILL.md`.

```text
.agent/skills/
└── <skill-name> -> ../../skills/<domain>/<skill-name>   ← flat symlink
.claude/skills/
└── <skill-name> -> ../../skills/<domain>/<skill-name>   ← flat symlink
```

> Do **not** symlink the entire `skills/` directory — agents will not discover nested subdirectories.

## Adding a New Skill

1. Create a new directory under `skills/<domain>/<skill-name>/`.
2. Copy `templates/SKILL.template.md` into that directory as `SKILL.md`.
3. Fill in the frontmatter and keep the body concise.
4. Add optional `references/`, `scripts/`, `templates/`, or `assets/` only when they materially improve reuse.
5. Add an entry to the skill table in this README.
6. Create flat symlinks in both `.agent/skills/` and `.claude/skills/`:
   ```bash
   ln -sf ../../skills/<domain>/<skill-name> .agent/skills/<skill-name>
   ln -sf ../../skills/<domain>/<skill-name> .claude/skills/<skill-name>
   ```

## Naming Guidance

- Directory names should use lowercase kebab-case.
- Skill `name` values should be stable and descriptive.
- Prefer names that state both target and action, such as `zach-wechat-daily-publisher` or `zach-article-publish-checklist`.

## Repository Hooks

A pre-commit hook in `.githooks/pre-commit` enforces the rules above: every skill under `skills/<domain>/<name>/SKILL.md` must have a README entry and matching flat symlinks under `.agent/skills/` and `.claude/skills/`. Orphan symlinks fail the hook too.

Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

If you must bypass it for a non-skill commit, use `git commit --no-verify`.
