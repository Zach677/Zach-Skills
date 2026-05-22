# Article Package Contract

The saved Markdown article is the source of truth. A separate
`article-package.json` is optional; use it only when a run needs machine-readable
intermediate data.

## Markdown Frontmatter

Every publishable article must start with:

```yaml
---
title: 文章标题
summary: 分享摘要
coverImage: /absolute/path/to/articles/imgs/YYYY-MM-DD-slug-cover.png
author: zachaics
---
```

Rules:

- `coverImage` must point to the final PNG used for this run.
- Do not point at `articles/imgs/cover.png` unless generation failed and the
  log says the generic fallback was reused.
- `summary` should be concise enough for WeChat share cards.
- Keep references in the Markdown body so facts can be checked later.

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
  "topic": {},
  "sources": [],
  "fact_checklist": [],
  "self_check": []
}
```

## Validation

Run:

```bash
python3 scripts/publisher_ops.py validate-article --article articles/YYYY-MM-DD-slug.md
```

The command checks frontmatter, title, summary, cover path, cover file, body
length, and minimum section count. The agent still owns editorial quality.
