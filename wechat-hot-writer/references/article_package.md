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
  - `X 之外，更值得关注的是 Y`
  - `从 X 看 Y 的落地逻辑`
  - `模型竞争背后，真正变化的是哪一层`
- Headline can carry judgment, but body should immediately anchor that judgment in a concrete person, company, product, or event

## Body skeleton

Use these exact section headings in the markdown scaffold:

1. `## 热点钩子`
2. `## 事实拆解`
3. `## 为什么现在重要`
4. `## 工具或案例`
5. `## 可执行建议`
6. `## 结尾观点`

The validator expects those headings unless the user explicitly changes the structure.

## Anti-AI-smell pass

Before packaging, fix these:

- Delete empty transition filler like “值得注意的是”“不难发现”
- Replace abstract nouns with concrete products, tools, companies, or actions
- Every non-obvious claim should map to a fact item or source URL
- Keep the tone restrained, precise, and useful
- Avoid obvious internet phrasing like “打起来了”“值钱”“热闹”“围观”
- Prefer analysis over performance, and judgment over hype
- Open with a concrete setup first, then move to the larger claim
- Prefer short, clean paragraphs or flat lists over dramatic transitions

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
