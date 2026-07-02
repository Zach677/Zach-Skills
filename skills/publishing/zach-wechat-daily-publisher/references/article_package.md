# Article Package Contract

The saved Markdown article is the source of truth. A separate
`article-package.json` is optional; use it only when a run needs machine-readable
intermediate data.

## Markdown Frontmatter

Every publishable article must start with the base fields:

```yaml
---
title: 文章标题
summary: 分享摘要
coverImage: /absolute/path/to/articles/imgs/YYYY-MM-DD-slug-cover.png
author: zachaics
---
```

When issue cover generation is in play, the orchestrator may add cover
compositor fields after the base fields:

```yaml
coverTitle: 封面短标题
coverSubtitle: 封面短副标题
coverVisualImage: /absolute/path/to/cover-image/slug/visual.png
illustrationManifest: /absolute/path/to/article-illustrations/YYYY-MM-DD/role-slug/manifest.json
```

Rules:

- `coverImage` must point to the final PNG used for this run.
- `coverTitle`, `coverSubtitle`, and `coverVisualImage` are orchestrator-owned
  fields for the local cover compositor. The writer may suggest wording in the
  brief, but should not add these fields unless explicitly asked.
- `illustrationManifest` is orchestrator-owned. It points to the article
  illustration manifest that records the outline, backend, prompt artifacts,
  generated raster images, and reference images.
- Do not point at `articles/imgs/cover.png` unless generation failed and the
  log says the generic fallback was reused.
- `summary` should be concise enough for WeChat share cards.
- Do not repeat the frontmatter title as a body H1. The WeChat draft title field
  already carries the title; start the body with the opening paragraph.
- Keep references in the Markdown body so facts can be checked later.
- Use `## 参考资料` for source lists. Links in that section are rendered as a
  compact source list and are not duplicated into another bottom citation block.

## Optional JSON Package

```json
{
  "date": "YYYY-MM-DD",
  "slug": "topic-slug",
  "title": "",
  "summary": "",
  "author": "",
  "article_path": "",
  "cover_image": "",
  "cover_visual_image": "",
  "cover_prompt": "",
  "illustration_manifest": "",
  "topic": {},
  "sources": [],
  "visual_plan": {},
  "fact_checklist": [],
  "self_check": []
}
```

## Validation

Run:

```bash
bun scripts/wechat_article_validate.ts --article articles/YYYY-MM-DD-role-slug.md
```

The command checks frontmatter, title, summary, cover path, cover file, body
length, and minimum section count. The agent still owns editorial quality.

For daily issues with inline illustrations, run:

```bash
bun scripts/daily_wechat_publisher.ts visual-qa --repo . --issue issues/YYYY-MM-DD.json --require-illustrations
```

This TypeScript QA checks that every article has `illustrationManifest`, an
outline, prompt files, generated raster images, inserted Markdown image links,
and rendered WeChat HTML references before publishing.
