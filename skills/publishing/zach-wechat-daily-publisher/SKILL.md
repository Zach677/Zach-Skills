---
name: zach-wechat-daily-publisher
description: "Use when Zach wants a full WeChat Official Account daily article workflow: API-only daily guard, history-aware topic choice, AI-written Simplified Chinese article, topic-specific cover generation, WeChat-ready rendering, API draft creation, publish/blocker logs, and learning from edits. Do not use browser, OpenCLI, Chrome, CDP, QR-login, or editor automation."
metadata:
  author: zach
  version: "0.1.0"
---

# Zach WeChat Daily Publisher

Use this skill for the daily WeChat Official Account loop. The agent owns
editorial judgment and writing; scripts own deterministic checks, rendering,
API calls, and logs.

## Hard Boundaries

- API-only publishing. Do not use browser publishing, OpenCLI, Chrome, CDP,
  Playwright, QR login, captcha handling, or editor automation.
- Do not publish twice on the same calendar date. Check success and blocker
  logs before choosing a topic or writing.
- If API publishing is blocked by network, credentials, IP whitelist, login
  policy, captcha, QR scan, or manual confirmation, save the local draft, write
  a blocker log, and stop.
- Writing is not scripted. The agent chooses the topic, researches facts,
  writes the article, self-edits, and only then calls deterministic scripts.

## Inputs

- Target repo, usually `/Users/star/Developer/zach-repo/Wechat-post`.
- Date, defaulting to the local calendar date in Asia/Shanghai.
- Existing article history and publish logs.
- Current public sources for factual, health, policy, weather, or consumer
  claims.
- Optional `EXTEND.md` preferences for lane, author, theme, cover, and comments.

## Workflow

Run these commands from the target publishing repo. The target repo owns the
TypeScript/Bun command surface; this skill owns the editorial contract,
reference rules, and the Baoyu renderer adapter under `scripts/`.

1. Preflight guard:
   ```bash
   bun scripts/daily_wechat_publisher.ts preflight --repo . --date today --fail-on-existing
   ```
2. Export history:
   ```bash
   bun scripts/daily_wechat_publisher.ts history-export --repo . --output .zach-wechat-daily-publisher/history.json
   ```
3. Capture the short-term traffic trend:
   ```bash
   bun scripts/daily_wechat_publisher.ts trend-scan --repo . --interval-minutes 180
   ```
4. Discover trend-aware topic candidates:
   ```bash
   bun scripts/daily_wechat_publisher.ts discover-topics --repo . --source-mode hybrid --limit 8
   ```
5. Pick exactly three coordinated topics: `main`, `side_a`, and `side_b`. The
   agent may use web research, exported history, and the latest trend scan. Load
   [references/topic_selection.md](references/topic_selection.md) for scoring
   rules.
6. Write three full Simplified Chinese articles. Load
   [references/article_writing.md](references/article_writing.md) and
   [references/article_package.md](references/article_package.md).
7. Save the articles under `articles/YYYY-MM-DD-role-slug.md`, where role is
   `main`, `side-a`, or `side-b`, with frontmatter: `title`, `summary`,
   `coverImage`, and `author`. Create `issues/YYYY-MM-DD.json` with exactly
   three articles.
8. Create cover prompt artifacts under
   `cover-image/<slug>/prompts/01-cover-<slug>.md` before generation. The
   generated bitmap should be a clean source visual without embedded copy; the
   repo-local compositor owns title/subtitle placement and crop-safe layout.
   Then run the target repo compositor:
   ```bash
   bun scripts/generate_issue_covers.ts --repo . --issue issues/YYYY-MM-DD.json --previews
   ```
   Next, run the baoyu article-illustrator workflow for inline article
   illustrations: analyze positions, write `outline.md`, save prompt files,
   resolve the image backend, generate raster images, insert local Markdown
   image links, and add `illustrationManifest` frontmatter. Never reuse
   `articles/imgs/cover.png` unless cover generation failed and the blocker/log
   explicitly says so. Load
   [references/cover_generation.md](references/cover_generation.md).
9. Validate and render:
   ```bash
   bun scripts/wechat_article_validate.ts --article articles/YYYY-MM-DD-main-slug.md
   bun scripts/wechat_render.ts --article articles/YYYY-MM-DD-main-slug.md --output articles/YYYY-MM-DD-main-slug.wechat.html
   ```
   Repeat validation/rendering for all three article files, or let
   `publish-issue` run these gates. Rendering uses the locked `baoyu-md` Bun
   adapter in this skill. The first run may install `scripts/` dependencies with
   `bun install --frozen-lockfile`. Before publishing, run visual QA:
   ```bash
   bun scripts/daily_wechat_publisher.ts visual-qa --repo . --issue issues/YYYY-MM-DD.json --require-illustrations
   ```
10. Publish through API only:
   ```bash
   bun scripts/daily_wechat_publisher.ts publish-issue --repo . --date today --issue issues/YYYY-MM-DD.json --api-only --require-illustrations
   ```
   Load [references/wechat_api_publish.md](references/wechat_api_publish.md).
11. `publish-issue` writes the success log or API blocker log. For a blocker
   before publish, write it with:
   ```bash
   bun scripts/daily_wechat_publisher.ts write-blocker --repo . --date today --blocker-type <type> --reason <reason>
   ```
   Load
   [references/logging_contract.md](references/logging_contract.md).

## Editorial Lane

Default readers are middle-aged and older adults, especially 45+ readers and
family caregivers. Prefer practical health, seasonal care, daily safety,
anti-scam, consumer, service-verification, and family-care topics. Avoid pure AI
industry news unless it clearly maps to mainstream livelihood or consumer risk.

Health, legal, policy, and financial claims must be verified and conservative.
Write general information, not diagnosis or treatment.

## References

- End-to-end shape: [references/pipeline.md](references/pipeline.md)
- Topic scoring: [references/topic_selection.md](references/topic_selection.md)
- Writing and self-check: [references/article_writing.md](references/article_writing.md)
- Article schema: [references/article_package.md](references/article_package.md)
- Visual generation: [references/cover_generation.md](references/cover_generation.md)
- WeChat rendering: [references/render_wechat_html.md](references/render_wechat_html.md)
- API publishing: [references/wechat_api_publish.md](references/wechat_api_publish.md)
- Logs: [references/logging_contract.md](references/logging_contract.md)
- Learning from edits: [references/learn_edits.md](references/learn_edits.md)
