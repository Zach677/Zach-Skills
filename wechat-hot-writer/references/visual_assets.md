# Visual Assets

Use Baoyu's image-related skills as the default visual layer for this skill.

## Mapping

- Cover image: `baoyu-cover-image`
- In-article diagrams and illustrations: `baoyu-article-illustrator`
- Batch image generation backend: `baoyu-image-gen`

## Practical workflow

1. Package the article first.
2. Run `prepare-visuals`.
3. Review the generated visual brief, outline, and prompts.
4. Use the emitted commands to generate cover and illustration assets.
5. Insert generated assets back into the article or use them as upload material.

## What `prepare-visuals` emits

- `visual-brief.json`: machine-readable summary of visual direction
- `cover/cover-brief.md`: cover intent, recommended Baoyu style, and ready command
- `illustrations/outline.md`: illustration positions and filenames
- `illustrations/prompts/*.md`: one saved prompt per illustration
- `illustrations/batch.json`: batch input for `baoyu-image-gen`
- `commands.json`: ready-to-run command set

## Default recommendations

For AI / tech commentary:

- Cover:
  - `baoyu-cover-image`
  - type: `conceptual`
  - style: `blueprint` or `editorial-infographic`
  - aspect: `16:9`
- In-article visuals:
  - `baoyu-article-illustrator`
  - preset: `tech-explainer` or `process-flow`
  - density: `balanced`
- Generation backend:
  - `baoyu-image-gen`
  - provider: auto-detect from configured keys
  - model: use provider-specific default, or override explicitly when needed

Current auto-detect order:

1. `google`
2. `openai`
3. `openrouter`
4. `dashscope`
5. `seedream`
6. `jimeng`
7. `replicate`

## Guardrails

- Do not generate random decorative filler just because a section exists.
- Prefer one strong diagram over three generic “AI concept art” images.
- Explanatory articles should bias toward framework, comparison, flowchart, and infographic types.
- Covers may be more symbolic; in-article visuals should stay explanatory.
