# Logging Contract

The target repo owns logs under `publish_logs/`.

## Success

```text
publish_logs/YYYY-MM-DD.json
```

Required fields:

- `date`
- `status: "draft_created"`
- `article_path`
- `title`
- `method: "wechat-api/draft-add"`
- `timestamp`
- `media_id`
- `cover_status`
- `frontmatter_coverImage`

## Blocker

```text
publish_logs/YYYY-MM-DD-blocker.json
```

Required fields:

- `date`
- `status: "blocked"`
- `blocked_at`
- `article_path`
- `title`
- `method`
- `blocker_type`
- `error`
- `cover_status`
- `frontmatter_coverImage`
- `notes`

## Cover Status

Use:

- `newly_generated`
- `reused_generic_cover`
- `generation_failed`

Always include the final cover path and prompt path when available.
