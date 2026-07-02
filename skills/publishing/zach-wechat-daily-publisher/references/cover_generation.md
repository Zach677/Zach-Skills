# Visual Generation

Use the useful parts of Baoyu's cover and article-illustrator contracts, but do
not blindly depend on those external skills at runtime. The local repo still
owns the WeChat card layout, crop safety, rendering, publishing, and logs. New
deterministic visual helper code should be TypeScript/Bun by default, with the
repo-local Python publisher acting as the stable wrapper when needed.

## Cover Source Images

Daily covers are a two-stage asset:

1. A generated source bitmap at `cover-image/<slug>/visual.png`.
2. A local compositor output at `articles/imgs/YYYY-MM-DD-slug-cover.png`.

The generated source bitmap is visual material only. It must not include
embedded Chinese titles, labels, role names, poster borders, or page chrome.
The local compositor places `coverTitle`, `coverSubtitle`, and the 1:1-safe
layout.

## Cover Dimensions

- `type`: `scene` or `conceptual` by default; use `minimal` for reminders and
  `metaphor` only when the metaphor is concrete and safe.
- `palette`: calm `warm`, `earth`, or `macaron` by default.
- `rendering`: `flat-vector` or hand-drawn educational illustration.
- `text`: `none` for the source bitmap.
- `mood`: `balanced` by default.
- `aspect`: `2.35:1`.

## Prompt Artifact Contract

For each article:

```text
cover-image/<slug>/
├── visual.png
└── prompts/01-cover-<slug>.md
```

Write the full final prompt file before generating or composing the cover. It
must contain:

- content context: article title, 1-2 sentence summary, 5-8 keywords
- visual design: type, palette, rendering, mood, text level, aspect
- composition: main visual, layout zones, empty-space plan
- constraints: no visible text, no labels, no realistic medical scenes, no
  alarming gore, no role labels
- references, only when reference image files are actually saved under `refs/`
  or another named artifact directory

If reference images are used, record concrete reproducible traits in the prompt:
layout, colors, icon vocabulary, line treatment, and the exact element that
should carry over. Do not add reference metadata for files that do not exist.

## Image Backend Selection

Resolve image generation backends with Baoyu's priority order:

1. Current-request override.
2. Saved preference in `EXTEND.md`.
3. Runtime-native bitmap generator. In Codex use native `imagegen`; in
   Cursor-style runtimes use `GenerateImage` if that is the native tool.
4. Non-native backend such as `codex-imagegen` or `baoyu-image-gen` when it is
   installed and available.
5. If no raster backend exists, block and log the reason.

Every backend receives a saved prompt file. Do not pass ad-hoc prompts that
cannot be audited later. Generate in batches when the backend supports it, but
keep one prompt file, output path, aspect ratio, and reference-image list per
task.

## Reference Images

Use reference images only when they are real saved files. Store them beside the
visual artifacts, describe their reusable traits, and record whether each
reference is used as `direct`, `style`, or `palette`. If a reference is only
verbally described, put the traits in the prompt text and do not add nonexistent
paths to manifest/frontmatter metadata.

## Article Illustrations

Borrow Baoyu Article Illustrator's full outline-first shape. Inline article
illustrations are normal daily artifacts when they add reader value.

Illustrate positions that clarify real reader tasks:

- a process with steps
- a comparison where two options are often confused
- a timeline or deadline sequence
- a checklist that readers will actually follow
- a framework or risk pattern the reader needs to recognize

Skip decorative scenes and literal metaphors. Write an outline before
generation, then save every final prompt under `prompts/`. Labels must use
actual terms from the article, stay short, and match the article language.
Inserted Markdown image paths must be relative to the article file so the
WeChat renderer can find and upload them.

Default preset: `hand-drawn-edu` (`infographic`, `sketch-notes`, `macaron`) when
the article has no stronger visual signal. Otherwise choose Type x
Style/Rendering x Palette deliberately:

- `type`: `infographic`, `scene`, `flowchart`, `comparison`, `framework`, or
  `timeline`
- `style/rendering`: `sketch-notes`, `flat-vector`, `editorial`, `minimal`, or
  another available style that matches the content
- `palette`: `macaron`, `warm`, `earth`, or style default
- `density`: `balanced` by default; use fewer images only when the article has
  fewer visualizable points

Artifact shape:

```text
article-illustrations/YYYY-MM-DD/<role>-<slug>/
├── outline.md
├── manifest.json
├── prompts/
│   └── 01-<type>-<slug>.md
└── 01-<type>-<slug>.png
```

The article frontmatter must include:

```yaml
illustrationManifest: article-illustrations/YYYY-MM-DD/<role>-<slug>/manifest.json
```

The manifest is the publishing contract:

```json
{
  "outline": "outline.md",
  "backend": "imagegen",
  "preset": "hand-drawn-edu",
  "density": "balanced",
  "illustrations": [
    {
      "position": "section title or paragraph anchor",
      "purpose": "why this helps the reader",
      "type": "process",
      "style": "sketch-notes",
      "palette": "macaron",
      "prompt": "prompts/01-process-example.md",
      "image": "01-process-example.png",
      "references": []
    }
  ]
}
```

Run the target repo's visual QA after rendering and before publishing:

```bash
python3 scripts/daily_wechat_publisher.py visual-qa --repo . --issue issues/YYYY-MM-DD.json --require-illustrations
```

## Rules

- Use runtime-native bitmap generation when available.
- Write prompt files before any generation.
- Do not use SVG/HTML/canvas as a raster substitute for generated artwork.
- Do not repair generated text by painting over a bitmap; regenerate or remove
  text from the source image.
- Do not reuse `articles/imgs/cover.png` unless generation fails; if reused,
  say so in the final report and log.
- Cover source fallback may be deterministic and local. Article illustrations
  are different: when `--require-illustrations` is active, missing manifests,
  prompts, raster files, or rendered HTML references block publishing.
