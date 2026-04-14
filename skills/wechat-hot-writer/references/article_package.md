# Article Package Contract

## Required output keys

The packaged article JSON should contain:

- `topic`
- `titles`
- `summary`
- `outline`
- `body_markdown`
- `body_html`
- `sources`
- `cover_prompt`
- `image_prompts`
- `keywords`
- `fact_checklist`

Optional but useful:

- `benchmark_article_url`
- `style_notes`
- `word_count`
- `validation`

## Titles

- Exactly 3, each with a different angle — do NOT submit 3 variations of the same template
- One of the three should read like a line someone might actually say out loud, not a headline
- Open with a concrete scene, sensation, number, time, or quote when possible — not with 「X」 placeholders
- Avoid these templated patterns (they scream AI-voice):
  - `看到「X」，先别急着…`
  - `说到「X」，更该看懂的是…`
  - `别把「X」只当新闻…`
  - `记住 "X" 原则，X 更 X`
  - Any title with a colon splitting "场景:建议" that starts with abstract weather/season words
- Prefer concrete over judgmental: `中午热得能穿短袖，晚上风一起还是凉` beats `春天穿衣要注意`
- Headline can carry a judgment, but the opening paragraph must anchor it in a specific person, scene, food, habit, time, or overheard quote — not an abstract statement about "the season" or "these days"
- When the topic is service / discount / travel / welfare, the title should imply `核对/提醒/步骤` in concrete words, not macro commentary

## Body skeleton

There is no fixed 6-section template. The scaffold generator may still emit default headings as a starting point, but the writer MUST rework them to fit the piece.

Rules for the final shape:

- 3 to 6 body sections, not always 6
- Section titles should be content, not category labels — write `脱衣服这件事，别只看中午` instead of `## 常见误区或案例`; write `天一暖就想减药，这事真不能自己拿主意` instead of `## 关键事实`
- Avoid numbered-count titles like `4 个坑`、`3 个信号`、`5 件事` unless the number is load-bearing (e.g. a real checklist of 3 items). They make the piece feel like a listicle generated from a template.
- Vary section length on purpose. If every section opens with a one-line intro, then a bullet list, then a bolded takeaway — the reader feels the template. Break the rhythm: some sections can be 2 paragraphs with no list at all.
- End with a short closing note. Don't literally title it `## 最后一句` or `## 最后提醒` every time — `## 写在最后`, `## 最后说一句`, or even no heading (just a horizontal rule) are fine.

## Anti-AI-Voice Pass

Before packaging, hunt these tells and fix them:

**Rhythm tells**
- The `不是 X，而是 Y` construction can appear at most twice in the whole article. AI loves stacking it 5+ times; humans don't.
- Same for `不仅仅是 X，更是 Y`, `表面上 X，其实 Y`, `看似 X，实则 Y` — one of each per article, max.
- Don't bold a "金句" at the end of every section. Bold sparingly — only when the line really is the takeaway.
- Don't break every 1–2 sentences into a new line for dramatic effect. Use normal paragraphs. Line breaks should mark a real beat, not pace a reveal.

**Voice tells**
- Cut faux-oral phrases that try too hard: `说白了`、`这事真别自己拍板`、`话说回来`、`一句话` (unless it genuinely is one line). Using them once is fine; stacking them reads fake.
- Cut empty transitions: `值得注意的是`、`不难发现`、`由此可见`、`综上所述`.
- Cut internet voice: `打起来了`、`值钱`、`热闹`、`围观`、`塌房`、`破防`.
- Cut fake authority: `医生都说`、`专家一致认为`、`所有人都应该`. Prefer `很多医生会提` / `有些医生的建议是` / `一般建议是`.

**Opening**
- Do NOT open with `这几天…`、`最近…`、`最近这段时间…` followed by an abstract claim about weather, trends, or society. That's the #1 AI-tell opening.
- Prefer one of these openings:
  - A small scene with a real person (family member, neighbor, a reader, yourself)
  - A specific number, time, or overheard quote
  - A direct statement of the stake for the reader (`家里有老人在吃降压药的，这几天真的要看一眼`)
- The first concrete noun in the article should appear before the 3rd sentence.

**Structure**
- Every non-obvious claim maps to a fact item or source URL.
- When the topic touches health, stay at general-information level. Clearly mark the "别拖、该就医" boundary, but don't manufacture urgency.
- No miracle claims, no fear-selling, no hard diagnosis language.

**Human voice markers (good to have, not required)**
- A first-person detail (`我妈`、`我爸`、`我自己家里`、`我那天`) once or twice, if genuine to the piece
- One admission of nuance or "我理解" before pushing back on a common assumption
- Concrete sensory detail (a time of day, a body part, a food, a neighborhood scene) at least once per section

## Reader Fit Checks

Before treating a draft as good enough, run these quick tests:

- `45+理解测试`: can a middle-aged or older reader understand the title and opening without extra context
- `群聊转述测试`: can the core point be retold in one calm sentence inside a family group
- `有用而不吓人`: does the piece give action and boundary, instead of just制造焦虑
- `健康边界测试`: if this is a wellness article, is it clearly not pretending to diagnose or prescribe
- `服务核对测试`: if this is a benefit or service piece, does it clearly tell the reader who qualifies, when it applies, and where to verify

## HTML rules

The renderer outputs WeChat-safe HTML from markdown.

Rules:

- Prefer plain markdown, not raw HTML
- No scripts, iframes, custom embeds, or arbitrary classes
- Keep tags simple: headings, paragraphs, lists, blockquotes, links, strong, em, code, image
- Images may stay as remote URLs in the package, but delivery should stage them into local files before editor upload

## Optional Baoyu renderer

If local `baoyu-markdown-to-html` is installed and runnable, produce a second HTML artifact as a styled WeChat-ready variant.

Use it as:

- a nicer browser-paste artifact
- a comparison point against the internal renderer
- a fallback when the user prefers the Baoyu theme system

Do not make the whole skill depend on it. If it fails, keep the internal HTML and continue.
