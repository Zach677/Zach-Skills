---
name: zach-wechat-daily-publisher
description: Use when Zach wants a full WeChat Official Account daily article workflow: API-only daily guard, history-aware topic choice, AI-written Simplified Chinese article, topic-specific cover generation, WeChat-ready rendering, API draft creation, publish/blocker logs, and learning from edits. Do not use browser, OpenCLI, Chrome, CDP, QR-login, or editor automation.
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

Run these commands from the target publishing repo unless a command explicitly
uses this skill directory.

1. Preflight guard:
   ```bash
   python3 /path/to/skill/scripts/publisher_ops.py preflight --repo . --date today --fail-on-existing
   ```
2. Export history:
   ```bash
   python3 /path/to/skill/scripts/publisher_ops.py history-export --repo . --output .zach-wechat-daily-publisher/history.json
   ```
3. Pick one timely topic. The agent may use web research and the exported
   history. Load [references/topic_selection.md](references/topic_selection.md)
   for scoring rules.
4. Write one full Simplified Chinese article. Load
   [references/article_writing.md](references/article_writing.md) and
   [references/article_package.md](references/article_package.md).
5. Save the article under `articles/YYYY-MM-DD-slug.md` with frontmatter:
   `title`, `summary`, `coverImage`, and `author`.
6. Create cover prompt artifacts:
   ```bash
   python3 /path/to/skill/scripts/publisher_ops.py cover-prompt --article articles/YYYY-MM-DD-slug.md --work-dir cover-image/slug
   ```
   Then use the runtime-native image tool to generate a bitmap cover, copy it to
   the exact `coverImage` path, and never reuse `articles/imgs/cover.png` unless
   cover generation failed and the blocker/log explicitly says so. Load
   [references/cover_generation.md](references/cover_generation.md).
7. Validate and render:
   ```bash
   python3 /path/to/skill/scripts/publisher_ops.py validate-article --article articles/YYYY-MM-DD-slug.md
   python3 /path/to/skill/scripts/publisher_ops.py render --article articles/YYYY-MM-DD-slug.md
   ```
8. Publish through API only:
   ```bash
   python3 /path/to/skill/scripts/publisher_ops.py publish-api --article articles/YYYY-MM-DD-slug.md --cover articles/imgs/YYYY-MM-DD-slug-cover.png
   ```
   Load [references/wechat_api_publish.md](references/wechat_api_publish.md).
9. Write either a success log or blocker log using
   `publisher_ops.py write-log`. Load
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
- Cover generation: [references/cover_generation.md](references/cover_generation.md)
- WeChat rendering: [references/render_wechat_html.md](references/render_wechat_html.md)
- API publishing: [references/wechat_api_publish.md](references/wechat_api_publish.md)
- Logs: [references/logging_contract.md](references/logging_contract.md)
- Learning from edits: [references/learn_edits.md](references/learn_edits.md)
