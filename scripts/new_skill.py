#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


def normalize_skill_name(raw_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw_name.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise ValueError("skill name must contain letters or numbers")
    return slug


def display_name_for(raw_name: str, slug: str) -> str:
    cleaned = raw_name.strip()
    if cleaned:
        return cleaned
    return slug.replace("-", " ").title()


def ensure_use_when(description: str) -> str:
    cleaned = description.strip()
    if not cleaned:
        return "Use when this skill should trigger for a reusable workflow in this repo."
    return cleaned if cleaned.lower().startswith("use when") else f"Use when {cleaned}"


def render_skill_md(slug: str, description: str, include_extend: bool) -> str:
    lines = [
        "---",
        f"name: {slug}",
        f"description: {description}",
        "---",
        "",
        f"# {slug.replace('-', ' ').title()}",
        "",
        "Replace this with the real workflow once the skill is defined.",
        "",
        "## Trigger Cases",
        "",
        "- Add concrete user requests that should trigger this skill",
        "- Add symptoms, contexts, or tools that make it relevant",
        "",
        "## Workflow",
        "",
        "1. Inspect the local context.",
        "2. Load only the references you actually need.",
        "3. Run the smallest reliable workflow.",
        "4. Verify results before claiming success.",
        "",
        "## Guardrails",
        "",
        "- Document the failure modes that matter.",
        "- Document tool or environment constraints.",
        "- Remove this placeholder text before shipping the skill.",
        "",
        "## Files To Load On Demand",
        "",
        "- [references/README.md](references/README.md)",
    ]
    if include_extend:
        lines[8:8] = [
            "If `EXTEND.md` exists for this skill, read it before acting and let it override non-secret preferences.",
            "",
        ]
    return "\n".join(lines) + "\n"


def render_skill_readme(display_name: str, slug: str, include_extend: bool, include_agent: bool) -> str:
    lines = [
        f"# {display_name}",
        "",
        f"`{slug}` is a scaffolded skill directory. Replace this README with the real setup and runbook.",
        "",
        "## Layout",
        "",
        "```text",
        f"skills/{slug}/",
        "├── SKILL.md",
        "├── README.md",
    ]
    if include_extend:
        lines.append("├── EXTEND.example.md")
    if include_agent:
        lines.append("├── agents/")
    lines.extend(
        [
            "├── references/",
            "└── scripts/",
            "```",
            "",
            "## Next Steps",
            "",
            "1. Replace placeholder text in `SKILL.md`.",
            "2. Add the real setup and usage notes here.",
            "3. Add references only when they pay for themselves.",
            "4. Add tests under the repo-level `tests/` directory.",
        ]
    )
    if include_extend:
        lines.extend(
            [
                "",
                "## Preferences",
                "",
                "If this skill needs non-secret user preferences, document them in `EXTEND.example.md` and teach the runtime how to load `EXTEND.md`.",
            ]
        )
    if include_agent:
        lines.extend(
            [
                "",
                "## Agent Metadata",
                "",
                "`agents/openai.yaml` is included as a starting point. Keep it only if this skill should expose agent-facing metadata.",
            ]
        )
    return "\n".join(lines) + "\n"


def render_extend_example(slug: str) -> str:
    return "\n".join(
        [
            f"# {slug} preferences",
            "# Copy this file to one of:",
            f"# - .baoyu-skills/{slug}/EXTEND.md",
            f"# - ${{XDG_CONFIG_HOME:-$HOME/.config}}/baoyu-skills/{slug}/EXTEND.md",
            f"# - ~/.baoyu-skills/{slug}/EXTEND.md",
            "#",
            "# Document real keys here once the skill supports them.",
            "",
            "example_setting: replace-me",
        ]
    ) + "\n"


def render_agent_yaml(display_name: str, slug: str) -> str:
    return "\n".join(
        [
            "interface:",
            f'  display_name: "{display_name}"',
            f'  short_description: "{display_name} skill scaffold"',
            f'  default_prompt: "Use ${slug} for the requested task."',
        ]
    ) + "\n"


def render_reference_readme() -> str:
    return "\n".join(
        [
            "# References",
            "",
            "Put long-form docs here only when the skill actually needs them.",
        ]
    ) + "\n"


def render_scripts_readme() -> str:
    return "\n".join(
        [
            "# Scripts",
            "",
            "Put local helper scripts here when the skill needs repeatable automation.",
        ]
    ) + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold_skill(
    repo_root: Path,
    raw_name: str,
    description: str,
    include_extend: bool,
    include_agent: bool,
) -> Path:
    slug = normalize_skill_name(raw_name)
    display_name = display_name_for(raw_name, slug)
    normalized_description = ensure_use_when(description)
    skill_dir = repo_root / "skills" / slug

    if skill_dir.exists():
        raise FileExistsError(f"skill already exists: {skill_dir}")

    write_text(skill_dir / "SKILL.md", render_skill_md(slug, normalized_description, include_extend))
    write_text(skill_dir / "README.md", render_skill_readme(display_name, slug, include_extend, include_agent))
    write_text(skill_dir / "references" / "README.md", render_reference_readme())
    write_text(skill_dir / "scripts" / "README.md", render_scripts_readme())

    if include_extend:
        write_text(skill_dir / "EXTEND.example.md", render_extend_example(slug))

    if include_agent:
        write_text(skill_dir / "agents" / "openai.yaml", render_agent_yaml(display_name, slug))

    return skill_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold a new skill directory in this repo")
    parser.add_argument("name", help="Human title or slug for the new skill")
    parser.add_argument(
        "--description",
        default="Use when this skill should trigger for a reusable workflow in this repo.",
        help='Frontmatter description. Prefer "Use when ..." phrasing.',
    )
    parser.add_argument("--with-extend", action="store_true", help="Include EXTEND.example.md")
    parser.add_argument("--with-agent", action="store_true", help="Include agents/openai.yaml")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repo root. Defaults to the parent of this scripts directory.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    created = scaffold_skill(
        repo_root=Path(args.repo_root).resolve(),
        raw_name=args.name,
        description=args.description,
        include_extend=args.with_extend,
        include_agent=args.with_agent,
    )
    print(created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
