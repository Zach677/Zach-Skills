---
name: wechat-hot-writer
description: Use when the user wants to find WeChat public account hot topics, turn them into AI/tech article packages with low AI smell, or stage drafts for mp.weixin.qq.com with an opencli-based delivery flow.
---

# WeChat Hot Writer

Use this skill for the full `find topic -> write article -> stage WeChat draft` loop.
Default lane: `泛科技AI`, draft-first, human final review.
If local `baoyu-post-to-wechat` credentials are configured, prefer the API draft path; otherwise fall back to browser draft staging.

## Trigger cases

- 微信公众号热点选题
- 自动写公众号文章
- 公众号草稿/发文自动化
- 热榜聚合后做 AI/科技内容
- 把现有公众号文章当风格参考，再批量出稿

## Workflow

1. Run topic discovery first.
   - Command: `python3 wechat-hot-writer/scripts/wechat_hot_writer.py discover-topics --limit 8 --output out/topics.json`
   - Load [references/topic_scoring.md](references/topic_scoring.md) if you need the schema, filters, or scoring details.
2. Pick one topic and create an article scaffold.
   - Command: `python3 wechat-hot-writer/scripts/wechat_hot_writer.py write-article --topic out/topics.json --topic-index 0 --scaffold out/draft.json`
3. Fill the scaffold.
   - Read [references/article_package.md](references/article_package.md) before writing.
   - Keep the section skeleton exact unless the user explicitly wants a different structure.
4. Package and validate the finished draft.
   - Command: `python3 wechat-hot-writer/scripts/wechat_hot_writer.py write-article --topic out/topics.json --topic-index 0 --draft out/draft.json --output out/article-package.json`
   - If local `baoyu-markdown-to-html` is installed and healthy, the packager also emits a styled WeChat HTML artifact beside the package.
5. Prepare visual assets.
   - Command: `python3 wechat-hot-writer/scripts/wechat_hot_writer.py prepare-visuals --package out/article-package.json --output-dir out/visuals`
   - Load [references/visual_assets.md](references/visual_assets.md) for the `baoyu-cover-image`, `baoyu-article-illustrator`, and `baoyu-image-gen` mapping.
   - The command auto-detects a usable image provider from configured keys. Override with `--provider` and `--model` only when you need to force a backend.
6. Stage delivery assets for WeChat.
   - Read [references/weixin_delivery.md](references/weixin_delivery.md) before running delivery.
   - Command: `python3 wechat-hot-writer/scripts/wechat_hot_writer.py deliver-weixin --package out/article-package.json --staging-dir out/weixin --dry-run`

## Guardrails

- Default to low-risk AI and tech topics.
- Filter or heavily down-rank finance, medical, legal, education, politics, and certification-sensitive topics unless the user explicitly opts in.
- Do not click final publish for personal or unverified accounts. Stop at draft or review-ready state.
- For browser-backed work, use `opencli`, not Playwright.
- Before non-trivial browser actions, check `opencli doctor`.
- If `mp.weixin.qq.com` lacks a stable built-in adapter, use `opencli explore`, then `opencli record` or `opencli generate` only if the user is already logged in and the session needs a site-specific flow.
- If local `baoyu-post-to-wechat` or `baoyu-markdown-to-html` tooling is available, use them as optional accelerators, not as hard dependencies.

## Files to load on demand

- Topic logic and filters: [references/topic_scoring.md](references/topic_scoring.md)
- Article package contract and HTML rules: [references/article_package.md](references/article_package.md)
- Visual asset preparation and Baoyu interop: [references/visual_assets.md](references/visual_assets.md)
- WeChat delivery flow and opencli guardrails: [references/weixin_delivery.md](references/weixin_delivery.md)
