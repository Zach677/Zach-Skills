---
name: wechat-hot-writer
description: Use when the user wants WeChat public account topic discovery, article packaging, or draft staging, especially for middle-aged, family, wellness, or public-interest accounts.
---

# WeChat Hot Writer

Use this skill for the full `find topic -> write article -> stage WeChat draft` loop.
Default lane: `中老年健康与银发生活`, draft-first, human final review.
When `EXTEND.md` exists, read it first and let it override lane, fallback query, title templates, style notes, and risk thresholds.

## Preferences

Check these paths in order:

1. `.baoyu-skills/wechat-hot-writer/EXTEND.md`
2. `${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/wechat-hot-writer/EXTEND.md`
3. `~/.baoyu-skills/wechat-hot-writer/EXTEND.md`

Use built-in defaults when no `EXTEND.md` exists.
Secrets still belong in `.env`, not `EXTEND.md`.

## Trigger cases

- 微信公众号热点选题
- 中老年/银发/养生/家庭向公众号选题
- 自动写公众号文章
- 公众号草稿/发文自动化
- 热榜聚合后做中老年、健康、银发生活、家庭关系内容
- 把现有公众号文章当风格参考，再批量出稿

## Workflow

Commands below assume the working directory is this skill directory.

1. If the user provides a benchmark爆款 or style reference, read it first and extract:
   - title pattern
   - opening move
   - section rhythm
   - what makes it easy to forward in family groups
   - what should be reused vs what should not be copied
2. Run topic discovery.
   - Command: `python3 scripts/wechat_hot_writer.py discover-topics --source-mode hybrid --limit 8 --history-file out/history.json --output out/topics.json`
   - Load [references/topic_scoring.md](references/topic_scoring.md) if you need schema, filters, or scoring details.
3. Pick one topic and decide the article lane before drafting:
   - `提醒型`: 误区、风险、注意事项
   - `实用型`: 饮食、睡眠、走路、家庭照护、季节建议
   - `人物/情感型`: 人物、家庭关系、社会观察
4. Create an article scaffold.
   - Command: `python3 scripts/wechat_hot_writer.py write-article --topic out/topics.json --topic-index 0 --scaffold out/draft.json`
5. Fill the scaffold.
   - Read [references/article_package.md](references/article_package.md) before writing.
   - Keep the section skeleton exact unless the user explicitly wants a different structure.
6. Run a pre-package writing check:
   - Can the target reader understand the title without niche context?
   - Can the main point be retold in one sentence inside a family group chat?
   - If the piece touches health, does it stay in general-information territory?
   - Did the article avoid fake urgency, miracle claims, and hard diagnosis language?
7. Package and validate the finished draft.
   - Command: `python3 scripts/wechat_hot_writer.py write-article --topic out/topics.json --topic-index 0 --draft out/draft.json --output out/article-package.json`
   - If local `baoyu-markdown-to-html` is installed and healthy, the packager also emits a styled WeChat HTML artifact beside the package.
8. Prepare visual assets.
   - Command: `python3 scripts/wechat_hot_writer.py prepare-visuals --package out/article-package.json --output-dir out/visuals`
   - Load [references/visual_assets.md](references/visual_assets.md) for `baoyu-cover-image`, `baoyu-article-illustrator`, and `baoyu-image-gen` mapping.
9. Stage delivery assets for WeChat.
   - Read [references/weixin_delivery.md](references/weixin_delivery.md) before running delivery.
   - Command: `python3 scripts/wechat_hot_writer.py deliver-weixin --package out/article-package.json --staging-dir out/weixin --dry-run`
10. After a publish or draft review, capture one short learning:
   - what title shape worked
   - what reader angle felt closest to the account
   - what should be down-ranked next time
11. After the draft is accepted or published, write it into history:
   - Command: `python3 scripts/wechat_hot_writer.py record-history --package out/article-package.json --history-file out/history.json --media-id <media_id>`
12. Later, sync article performance back into history:
   - Command: `python3 scripts/wechat_hot_writer.py sync-history-stats --history-file out/history.json --days 7`

## Guardrails

- Default to readers aged roughly 45+ and their family caregivers unless `EXTEND.md` clearly says otherwise.
- Prefer health, wellness, sleep, diet, walking, joints, blood sugar, digestion, seasonal care, silver-life, family concerns, anti-scam reminders,人物故事, and public-interest lifestyle topics.
- AI topics are allowed only when attached to a mainstream livelihood, food, consumer, or social hotspot with obvious mass interest.
- Filter or heavily down-rank finance, diagnosis-heavy medical, legal, education, politics, and certification-sensitive topics unless the user explicitly opts in.
- For health and wellness content, stay at the level of general information and daily habits.
- Do not click final publish for personal or unverified accounts. Stop at draft or review-ready state.
- For browser-backed work, use `opencli`, not Playwright.
- Before non-trivial browser actions, check `opencli doctor`.
- If local `baoyu-post-to-wechat` or `baoyu-markdown-to-html` tooling is available, use them as accelerators, not hard dependencies.

## Files to load on demand

- Topic logic and filters: [references/topic_scoring.md](references/topic_scoring.md)
- Article package contract and HTML rules: [references/article_package.md](references/article_package.md)
- Visual asset prep and Baoyu interop: [references/visual_assets.md](references/visual_assets.md)
- WeChat delivery flow and opencli guardrails: [references/weixin_delivery.md](references/weixin_delivery.md)
