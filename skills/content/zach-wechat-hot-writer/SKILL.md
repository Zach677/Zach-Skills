---
name: zach-wechat-hot-writer
description: Use when the user wants WeChat public account topic discovery, article packaging, or draft staging, especially for middle-aged, family, wellness, anti-fraud, personal-info-safety, reservation-reminder, consumer-reminder, or silver-service accounts.
---

# Zach WeChat Hot Writer

Use this skill for the full `find topic -> write article -> stage WeChat draft` loop.
Default lane: `中老年健康与银发生活`, with practical sub-lanes for `健康提醒`, `防骗避坑`, `个人信息/支付安全`, `朋友圈辟谣`, and `银发服务/出行/认证核对`; draft-first, human final review.
When `EXTEND.md` exists, read it first and let it override lane, fallback query, title templates, style notes, and risk thresholds.

## Preferences

Check these paths in order:

1. `.baoyu-skills/zach-wechat-hot-writer/EXTEND.md`
2. `${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/zach-wechat-hot-writer/EXTEND.md`
3. `~/.baoyu-skills/zach-wechat-hot-writer/EXTEND.md`

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
   - whether it wins by `提醒`, `核对`, `清单`, `步骤`, or `家庭情绪共鸣`
   - what should be reused vs what should not be copied
2. Run topic discovery.
   - Command: `python3 scripts/wechat_hot_writer.py discover-topics --source-mode hybrid --limit 8 --history-file out/history.json --output out/topics.json`
   - Load [references/topic_scoring.md](references/topic_scoring.md) if you need schema, filters, or scoring details.
3. Pick one topic and decide the article lane before drafting:
   - `提醒型`: 误区、风险、注意事项
   - `实用型`: 饮食、睡眠、走路、家庭照护、季节建议
   - `服务/消费型`: 防骗、回收、价格、福利、出行、办事提醒
   - `信息安全型`: 身份证、复印件、刷脸、验证码、陌生链接、官方入口核实
   - `辟谣核对型`: 朋友圈假消息、AI造谣、假通知、新规传闻、官方通报
   - `家庭观察型`: 只在能落到具体家庭动作或边界提醒时保留
4. Create an article scaffold.
   - Command: `python3 scripts/wechat_hot_writer.py write-article --topic out/topics.json --topic-index 0 --scaffold out/draft.json`
5. Fill the scaffold.
   - Read [references/article_package.md](references/article_package.md) before writing.
   - The 6-section scaffold from `scaffold_article` is a starting shape, not a final structure. Before packaging, rework section headings so they describe the actual content (e.g. `脱衣服这件事，别只看中午`), not category labels (e.g. `常见误区或案例`). 3–6 sections, varied lengths, no forced numbered-count titles (`4 个坑`, `3 个信号`) unless the number is real.
6. Run a pre-package writing check:
   - **AI-voice self-audit** (see `references/article_package.md` → Anti-AI-Voice Pass):
     - Does the opening start with `这几天…` / `最近…` + abstract weather-or-trend claim? If yes, rewrite to a concrete scene, person, number, or quote.
     - Count uses of `不是 X，而是 Y` — more than 2? Cut down.
     - Every section ending with a bolded金句? Thin it out.
     - Section titles reading like category labels (`关键事实`, `常见误区`, `最后提醒`)? Rewrite as content lines.
     - Titles all matching one `看到「X」…` / `别把「X」…` / `说到「X」…` template? Diversify — at least one should read like something said out loud.
   - Can the target reader understand the title without niche context?
   - Can the main point be retold in one sentence inside a family group chat?
   - If this is a service, benefit, or consumer piece, did it clearly say `适用于谁 / 什么时候 / 去哪核对 / 不要误会什么`?
   - If this is a rumor, fake-notice, or new-rule piece, did it clearly say `原消息从哪来 / 官方说法是什么 / 哪些说法别转发 / 去哪核实`?
   - If this is a reservation,实名, or official-service piece, did it clearly say `入口 / 条件 / 时间点 / 是否需要身份证或实名验证`?
   - If this is a pension, social-security, or allowance-certification piece, did it clearly say `谁需要主动认证 / 何时可能停发 / 线上线下入口 / 家属怎么帮忙核对`?
   - If this is an identity, payment, or privacy piece, did it clearly say `什么不能给 / 去哪核实 / 发现异常先做什么`?
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
- Prefer health, wellness, sleep, diet, walking, joints, blood sugar, digestion, seasonal care and weather reminders, silver-life, anti-scam reminders, personal-info safety, rumor/fake-notice verification, service/welfare verification, pension or allowance certification reminders, reservation reminders, travel or benefit reminders, and public-interest lifestyle topics that clearly map back to ordinary family decisions.
- AI topics are allowed only when attached to a mainstream livelihood, food, consumer, or social hotspot with obvious mass interest.
- Filter or heavily down-rank finance, diagnosis-heavy medical, legal, education, politics, and certification-sensitive topics unless the user explicitly opts in.
- Filter or heavily down-rank pure celebrity gossip, youth-internet slang topics, entertainment `塌房` chatter, and abstract social commentary with no concrete family action.
- Filter or heavily down-rank人物/情感/社会观察选题 when they cannot be rewritten into a concrete `提醒 / 核对 / 止损 / 日常动作`.
- For health and wellness content, stay at the level of general information and daily habits.
- For service, discount, ticketing, or welfare topics, stay at the level of official facts, eligibility checks, timing, and action steps; do not drift into policy interpretation.
- For rumor, fake-notice, or new-rule topics, stay at the level of source checking, official clarification, affected scope, and family-group forwarding advice; do not amplify the rumor as if it were fact.
- For identity, payment, or privacy topics, stay at the level of official channels, minimum-necessary information, and stop-loss actions; do not invent platform rules.
- Do not click final publish for personal or unverified accounts. Stop at draft or review-ready state.
- For browser-backed work, use `opencli`, not Playwright.
- Before non-trivial browser actions, check `opencli doctor`.
- If local `baoyu-post-to-wechat` or `baoyu-markdown-to-html` tooling is available, use them as accelerators, not hard dependencies.

## Files to load on demand

- Topic logic and filters: [references/topic_scoring.md](references/topic_scoring.md)
- Article package contract and HTML rules: [references/article_package.md](references/article_package.md)
- Visual asset prep and Baoyu interop: [references/visual_assets.md](references/visual_assets.md)
- WeChat delivery flow and opencli guardrails: [references/weixin_delivery.md](references/weixin_delivery.md)
