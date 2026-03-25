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

- Exactly 3
- Useful, specific, not clickbait sludge
- Default style:
  - `从「X」说起，很多家庭都容易忽视这件事`
  - `看到「X」，更该提醒家里人的是这几个细节`
  - `别只盯着「X」，真正要紧的是后面这一步`
- Headline can carry judgment, but body should immediately anchor that judgment in a concrete person, family scene, daily habit, food item, or public event

## Body skeleton

Use these exact section headings in the markdown scaffold:

1. `## 热点钩子`
2. `## 这事和谁最相关`
3. `## 关键事实`
4. `## 常见误区或案例`
5. `## 日常怎么做`
6. `## 最后提醒`

The validator expects those headings unless the user explicitly changes the structure.

## Anti-Slop Pass

Before packaging, fix these:

- Delete empty transition filler like “值得注意的是”“不难发现”
- Replace abstract nouns with concrete people, foods, habits, family scenes, or actions
- Every non-obvious claim should map to a fact item or source URL
- Keep the tone restrained, precise, and useful
- Avoid obvious internet phrasing like “打起来了”“值钱”“热闹”“围观”
- Avoid pseudo-health fear selling, miracle claims, and fake authority voice
- Prefer useful explanation over performance, and calm reminders over hype
- Open with a concrete setup first, then move to the larger claim
- Prefer short, clean paragraphs or flat lists over dramatic transitions
- When the topic touches health, keep it at general-information level and clearly mark any “don’t拖、该就医”的边界

## Reader Fit Checks

Before treating a draft as good enough, run these quick tests:

- `45+理解测试`: can a middle-aged or older reader understand the title and opening without extra context
- `群聊转述测试`: can the core point be retold in one calm sentence inside a family group
- `有用而不吓人`: does the piece give action and boundary, instead of just制造焦虑
- `健康边界测试`: if this is a wellness article, is it clearly not pretending to diagnose or prescribe

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
