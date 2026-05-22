# Cover Generation

Use Baoyu Cover Image's useful contract, but do not depend on the external skill
at runtime.

## Dimensions

- `type`: scene, conceptual, typography, metaphor, minimal
- `palette`: warm, elegant, cool, earth, pastel, duotone, macaron
- `rendering`: flat-vector by default
- `text`: title-only by default
- `mood`: balanced by default
- `aspect`: `2.35:1` by default

## Artifact Contract

For each article:

```text
cover-image/<slug>/
├── source-<slug>.md
├── prompts/01-cover-<slug>.md
└── cover.png
```

The final article cover must be copied to:

```text
articles/imgs/YYYY-MM-DD-slug-cover.png
```

The article frontmatter `coverImage` must point to that final PNG.

## Rules

- Use runtime-native bitmap generation when available.
- Write the full prompt file before generating.
- Do not use SVG/HTML/canvas as a raster substitute.
- Do not repair generated text by painting over a bitmap.
- Do not reuse `articles/imgs/cover.png` unless generation fails; if reused,
  say so in the final report and log.
